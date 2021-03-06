## Use XMPP auth

PRO

- already done

CONS

- Does not provide the proxy user IP address, which could be « legally » useful when logging consent?

TODO

- This is used as temporary shorthand, it has good chances to be changed in the future
- For now the recommandation is that every user uses its own xmpp server
- require something to be signed with the user server domain certificate?
- Would this allow us to even get an identity, which would be more usable that IP address

## Use Ad hoc commands to retrieve data

- Check exemples of errors handled in ad-hoc commands
- Localize error message?

## Directly return data in the iq response

TODO

## Expose application specific errors

- Date: 2020-09-14
- Status: proposed
- Deciders: Cyril Lugan

### Context

Some application specific details might interest client applications to handle errors.

Ex. « This consumer has no communicating energy meter. »

For now, those errors happen when requesting  data through [XEP-0050: Ad-Hoc Commands](https://xmpp.org/extensions/xep-0050.html).

### Candidates

1. Parse and return the error in an iq :

   ```xml
   <iq xml:lang="en" to="…" type="error" id="…">
     <error type="cancel">
       <undefined-condition xmlns="urn:ietf:params:xml:ns:xmpp-stanzas" />
        <text xmlns="urn:ietf:params:xml:ns:xmpp-stanzas">The requested period cannot be anterior to the meter&apos;s last activation date</text>
        <upstream-error xmlns="urn:quoalise:0" issuer="enedis-data-connect" code="ADAM-ERR0123" />
     </error>
   </iq>
   ```

2. Return the raw error in an ad-hoc command flow :

   ```xml
   <iq xml:lang="en" to="…" type="result" id="…">
     <command xmlns="http://jabber.org/protocol/commands" node="…" sessionid="…" status="completed">
       <note type="error">{
     &quot;error&quot;: &quot;ADAM-ERR0123&quot;,
     &quot;error_description&quot;: &quot;The requested period cannot be anterior to the meter&apos;s last activation date&quot;                   
   }
    </note>
     </command>
   </iq>        
   ```

### Decision

Return the error in an iq :

- Seems more extensible
- Consistent with slixmpp handling of exception not catched by user code
- Provide a way to expose the raw upstream application error code, attributes might be added

## Use XMPP

- Date: 2019-03-19
- Id: <a name="use-senml">use-xmpp</a>
- Status: proposed
- Deciders: Gautier Husson, Gregory Elleouet

Use XMPP

See [Rapport d’évaluation des protocoles d’échange de données fédéré](https://github.com/consometers/sen1-poc-docs/blob/master/Rapport-choix-protocole.pdf) (fr)