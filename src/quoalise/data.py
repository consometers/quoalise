from collections import defaultdict
from typing import Union, Optional, Iterable, Tuple, Dict, List, Any
import datetime as dt
from slixmpp.xmlstream import ET
import zoneinfo
import json

#
# Quick and dirty quoalise data interface, to be improved / documented
#


class Record:
    def __init__(
        self,
        name: str,
        time: Optional[dt.datetime],
        unit: Optional[str],
        value: Union[float, int, None] = None,
    ) -> None:

        self.name = name
        self.time = time
        self.value = value
        self.unit = unit

    def __str__(self) -> str:
        return f"<Record {self.name} {self.time} {self.value} {self.unit}>"


class Sensml:
    def __init__(self, xml_element: Optional[ET.Element] = None) -> None:
        if xml_element is None:
            self.xml_element = ET.Element("{urn:ietf:params:xml:ns:senml}sensml")
        else:
            self.xml_element = xml_element

    @staticmethod
    def timestamp(time: dt.datetime) -> float:
        assert (
            time.tzinfo is not None
        ), "Naive datetimes are not handled to prevent errors"
        return time.astimezone(zoneinfo.ZoneInfo("UTC")).timestamp()

    def append(self, record: Record) -> None:

        # Instead of looking for current bn, bt, bv, bu from previous
        # records, reset them all for now.
        # compress() can be used to get more sensible senml output

        senml = ET.Element(
            "{urn:ietf:params:xml:ns:senml}senml",
            bn=record.name,
        )

        if record.time is not None:
            senml.attrib["bt"] = str(Sensml.timestamp(record.time))

        if record.value is not None:
            senml.attrib["bv"] = str(record.value)

        if record.unit is not None:
            senml.attrib["bu"] = str(record.unit)

        self.xml_element.append(senml)

    def extend(self, records: Iterable[Record]) -> None:
        for record in records:
            self.append(record)

    def compress(self) -> None:
        """
        Dumb stream compressor
        """
        base_name = None
        base_time = None
        units = set()
        for record in self.records():
            # Set base time to the earliest time in series
            if base_time is None or record.time < base_time:
                base_time = record.time
            # Set base name to the longest common starting substring
            if base_name is None:
                base_name = record.name
            else:
                while not record.name.startswith(base_name):
                    base_name = base_name[:-1]
            # Collect all units
            units.add(record.unit)

        if len(units) == 1:
            first = True
            for record, elem in self.__records_with_elements():
                if first:
                    elem.attrib["bu"] = units.pop()
                    first = False
                else:
                    elem.attrib.pop("bu", None)
                elem.attrib.pop("u", None)

        if base_name:
            first = True
            for record, elem in self.__records_with_elements():
                if first:
                    elem.attrib["bn"] = base_name
                    first = False
                else:
                    elem.attrib.pop("bn", None)
                assert record.name.startswith(base_name)
                name = record.name[len(base_name) :]
                if name:
                    elem.attrib["n"] = name
                else:
                    elem.attrib.pop("n", None)

        if base_time:
            base_timestamp = int(Sensml.timestamp(base_time))
            first = True
            for record, elem in self.__records_with_elements():
                assert record.time is not None
                if first:
                    elem.attrib["bt"] = str(base_timestamp)
                    first = False
                else:
                    elem.attrib.pop("bt", None)
                time = Sensml.timestamp(record.time)
                time = round(time - base_timestamp, 1)
                if time != 0.0:
                    elem.attrib["t"] = str(time)
                else:
                    elem.attrib.pop("t", None)

        # Do not handle base value for now
        for record, elem in self.__records_with_elements():
            elem.attrib.pop("bv", None)
            elem.attrib["v"] = str(record.value)

    def __records_with_elements(self) -> Iterable[Tuple[Record, ET.Element]]:

        base_name = None
        base_time = None
        base_unit = None
        base_value = None

        for elem in self.xml_element.findall("./{urn:ietf:params:xml:ns:senml}senml"):
            if "bn" in elem.attrib:
                base_name = elem.attrib["bn"]
            if "bt" in elem.attrib:
                base_time = float(elem.attrib["bt"])
            if "bu" in elem.attrib:
                base_unit = elem.attrib["bu"]
            if "bv" in elem.attrib:
                base_value = float(elem.attrib["bv"])

            name = elem.attrib.get("n", None)
            if base_name is not None:
                name = base_name + name if name is not None else base_name

            time = elem.attrib.get("t", None)
            if time is not None:
                time = float(time)
            if base_time is not None:
                time = base_time + time if time is not None else base_time
            if time is not None:
                time = dt.datetime.utcfromtimestamp(time)
                time = time.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))

            unit = elem.attrib.get("u", None)
            if base_unit is not None:
                unit = base_unit + unit if unit is not None else base_unit

            value = elem.attrib.get("v", None)
            if value is not None:
                value = float(value)
            if base_value is not None:
                value = base_value + value if value is not None else base_value

            record = Record(name, time, unit, value)

            yield record, elem

    def records(self) -> Iterable[Record]:
        for record, _ in self.__records_with_elements():
            yield record


class Metadata:
    def __init__(self, as_dict: Dict[str, Any] = {}) -> None:
        self.as_dict = as_dict

    @classmethod
    def from_xml(cls, element: ET.Element) -> "Metadata":
        assert element.tag == "{urn:quoalise:0}meta"
        as_dict = cls.xml_to_dict(element)["meta"]
        return Metadata(as_dict)

    def to_xml(self) -> ET.Element:
        element = ET.Element("{urn:quoalise:0}meta")
        Metadata.dict_to_xml(element, self.as_dict)
        return element

    @classmethod
    def dict_to_xml(cls, parent: ET.Element, as_dict: Dict[str, Any]) -> None:
        for name, child in as_dict.items():
            if name == "#text":
                raise RuntimeError("Not implemented yet")
            if isinstance(child, dict):
                element = ET.Element("{urn:quoalise:0}" + name)
                parent.append(element)
                cls.dict_to_xml(element, child)
            else:
                parent.attrib[name] = child

    @classmethod
    def xml_to_dict(cls, t: ET.Element) -> Dict[str, Any]:
        # From K3---rnc on
        # https://stackoverflow.com/questions/7684333/converting-xml-to-dictionary-using-elementtree
        _, _, t.tag = t.tag.rpartition("}")  # strip ns
        d: Dict[str, Any] = {t.tag: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(cls.xml_to_dict, children):
                for k, v in dc.items():
                    dd[k].append(v)
            d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
        if t.attrib:
            d[t.tag].update((k, v) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[t.tag]["#text"] = text
            else:
                d[t.tag] = text
        return d


class Data:
    def __init__(
        self,
        metadata: Optional[Metadata] = None,
        sensml: Optional[Sensml] = None,
        records: Optional[Iterable[Record]] = None,
    ) -> None:

        if metadata is None:
            self.metadata = Metadata()
        else:
            self.metadata = metadata
        if sensml is None:
            self.sensml = Sensml()
            if records is not None:
                self.sensml.extend(records)
        else:
            assert records is None
            self.sensml = sensml

    @classmethod
    def from_xml(cls, element: ET.Element) -> "Data":
        assert element.tag == "{urn:quoalise:0}data"
        meta = element.find("./{urn:quoalise:0}meta")
        meta = Metadata.from_xml(meta)

        sensml = element.find("./{urn:ietf:params:xml:ns:senml}sensml")
        sensml = Sensml(sensml)

        return Data(meta, sensml)

    def to_xml(self) -> ET.Element:
        element = ET.Element("{urn:quoalise:0}data")
        element.append(self.metadata.to_xml())
        self.sensml.compress()
        element.append(self.sensml.xml_element)
        return element

    def to_json(
        self, indent: Optional[int] = None, tz: Optional[dt.tzinfo] = None
    ) -> str:
        def serialize(obj: Any) -> Union[str, Dict[str, Any]]:
            if isinstance(obj, dt.datetime):
                return obj.astimezone(tz=tz).isoformat()
            if isinstance(obj, Record):
                return obj.__dict__
            return str(obj)

        return json.dumps(
            {"meta": self.metadata.as_dict, "records": list(self.sensml.records())},
            indent=indent,
            default=serialize,
        )

    # Kept to avoid breaking previous API, might be deprecated soon

    @property
    def meta(self) -> Dict[str, Any]:
        return self.metadata.as_dict

    @property
    def records(self) -> List[Record]:
        return list(self.sensml.records())
