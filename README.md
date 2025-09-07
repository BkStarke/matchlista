# Starke Träningsläger System #  
GitHub Repo för BK Starkes träningsläger system och hemsida.  
Denna hemsidan och hur man använder den är open source och du får gärna lov att använda den för ditt eget träningsläger.  
Hör gärna av er om ni använt det och ifall ni har förslag på förbättringar.  
*Uppdaterad senast under träningslägret 7e september 2025*

## Hur man använder det ##

### Excel förberedning ###  

Börja med att skapa en lista på alla deltagarna i en excel sheet.  
Första kolumnen ska vara deltagarens namn *kan inkludera efternamn, spelar ingen roll*.  
Andra kolumnen ska innehålla deltagerns brottningsklubb.  
Tredje kolumnen ska innehålla vilken grupp som brottaren ska delta i.  


### Skapa lottningen ###  
Kopiera alla dem första tre kolumnerna av dem personerna du vill ska brottas på samma matta.  
Endast dem med samma grupp nummer kommer att möta varandra.  
Kör `lottning.py` och klistra in dem första tre kolumnerna när dem ber om det.  
Sedan kommer du få välja hur många matcher som ska gås på mattan.  
Den kommer att mata ut information om hur många matcher varje person.  
Ovanför det så hittar du alla matcherna som lottats.  
Varje person på mattan kommer att få lika många matcher med 1 matchs marginal.  


### Vad du gör med lottningen ###   
Börja med att skapa ett nytt ark i excel filen.  
Här ska första kolumnen vara match#.  
Andra kolumnen vilken matchtid som matchen börjar.  
Tredje kolumnen och frammåt är alla mattorna.  
I ordning så ska första raden vara  `Match#`, `Tid`, `Matta 1`, `Matta 2`, osv.
Klistra sedan in lottningen från `lottning.py` i dem Matt# kolumnerna du vill dem ska gå.  
Kolumnen `Match#` ska bara ha vilken runda av matcher som det är.  
Kolumnen `Tid` ska ha vilken start tid som matchen är.  
Om du exempelvis vill ha 3 minuter match med 1 minut vila så ska det vara 4 minuter mellan starttider.  
Om du vill ha 2 minuter med ingen vila så ta 2 minuter mellan matcherna.  

### Infoga till hemsidan ###   
För att infoga i hemsidan så kör du programmet `ändra_HTML.pyw`.  
Här ska du välja excel filen och arket som du har lottningen i.  
Under så välj hur lång vilotid du vill ha mellan matcherna, om du vill ha vilotid.  
Sedan tryck på `Ändra HTML` och så kommer filen att skapa/uppdatera `json.json`, `tabell.html` och `tid.html`.  
Sedan är hemsidan klar och du kan hosta den.  

### Ska fixas till nästa gång ###  
Måste fixa lottningen så att det är mindre sannolikhet att en person går flera matcher i rad.  
Be om att anmälningarna ska ske till ansvarig mejl i en excel format så att det sker smidigare.  
Fixa så att en person inte möter flera personer i rad, även om det är matcher mellan.  
Programera om så att det blir så jämnt avstånd mellan matcherna som möjligt.  
Implementera ett system för att uppdatera matcherna on the fly.  
En sök funktion så man kan söka efter brottare längt upp p sidan.  