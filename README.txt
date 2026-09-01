# Sophämtningskalendern Sysav

Sophämtningskalendern Sysav visar när dina sopkärl ska tömmas direkt i Homey. Appen hämtar det aktuella tömningsschemat från Sysav utifrån din adress och hjälper dig att komma ihåg när det är dags att ställa fram kärlen.

## Så fungerar det

När du lägger till en enhet anger du gata, gatunummer och ort. Appen hämtar sedan de avfallstyper som finns registrerade för adressen, till exempel Kärl 1, Matavfall eller Trädgårdsavfall. Varje vald avfallstyp läggs till som en egen enhet i Homey.

På enhetens kort visas:

- datumet för nästa hämtning
- antal dagar kvar till hämtningen

Schemat kontrolleras automatiskt varje timme. Flera enheter på samma adress delar på hämtningen av data, vilket minskar antalet anrop till Sysav.

## Automatisera med Flow

Appen innehåller Flow-kort som kan användas för att skicka påminnelser eller starta andra automatiseringar:

- när hämtningen är idag
- när hämtningen är imorgon
- när nästa hämtningsdatum ändras
- kontrollera om hämtningen sker om ett visst antal dagar

Du kan till exempel skicka en pushnotis kvällen före hämtning, tända en lampa som påminnelse eller meddela hushållet när Sysav ändrar ett datum.

## Förutsättningar

Adressen måste finnas i Sysavs tömningsschema. Om appen inte hittar adressen kan du kontrollera hur den är registrerad på sysav.se och använda samma stavning när du lägger till enheten i Homey.
