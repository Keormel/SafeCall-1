// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Romanian Moldavian Moldovan (`ro`).
class AppLocalizationsRo extends AppLocalizations {
  AppLocalizationsRo([String locale = 'ro']) : super(locale);

  @override
  String get appName => 'SafeCall';

  @override
  String get ok => 'OK';

  @override
  String get cancel => 'Anulează';

  @override
  String get close => 'Închide';

  @override
  String get retry => 'Reîncearcă';

  @override
  String get done => 'Gata';

  @override
  String get yes => 'Da';

  @override
  String get no => 'Nu';

  @override
  String get errNoConnection => 'Nu există conexiune, încercați mai târziu';

  @override
  String get errGeneric => 'Ceva n-a mers bine. Încercați din nou';

  @override
  String get errRateLimited => 'Prea multe cereri. Încercați mai târziu';

  @override
  String get errInvalidPhone => 'Verificați numărul de telefon';

  @override
  String get errDuplicateReport => 'Ați raportat deja acest număr astăzi';

  @override
  String get errAssistantUnavailable =>
      'Asistentul nu este disponibil acum. Încercați mai târziu';

  @override
  String get riskHigh => 'Pericol';

  @override
  String get riskHighHint =>
      'Posibilă fraudă. Nu comunicați coduri și nu transferați bani';

  @override
  String get riskMedium => 'Atenție';

  @override
  String get riskMediumHint =>
      'Există semne asemănătoare cu o schemă de fraudă cunoscută';

  @override
  String get riskLow => 'Puține plângeri';

  @override
  String get riskLowHint => 'Acest număr a fost raportat rar';

  @override
  String get riskUnknown => 'Număr necunoscut';

  @override
  String get riskUnknownHint =>
      'Încă nu avem suficiente informații despre acest număr. Nu comunicați codurile din SMS și datele bancare';

  @override
  String get catBank => 'Bancă';

  @override
  String get catPolice => 'Poliție';

  @override
  String get catDelivery => 'Livrare';

  @override
  String get catRelative => 'Rudă';

  @override
  String get catInvestment => 'Investiții';

  @override
  String get catOther => 'Altceva';

  @override
  String get onb1Title => 'Nu ascultăm convorbirile';

  @override
  String get onb1Body =>
      'SafeCall nu înregistrează și nu analizează sunetul, nu citește contactele și nu vă află numele.';

  @override
  String get onb2Title => 'Verificăm doar numărul';

  @override
  String get onb2Body =>
      'Numărul apelantului este verificat într-o bază aflată chiar pe telefonul dvs. — chiar și fără internet.';

  @override
  String get onb3Title => 'Activați protecția';

  @override
  String get onb3Body =>
      'Permiteți notificările ca să vă putem avertiza în timpul apelului. Apelurile nu sunt blocate niciodată — dvs. decideți dacă răspundeți.';

  @override
  String get onbNext => 'Înainte';

  @override
  String get onbSkip => 'Omite';

  @override
  String get onbEnable => 'Activează protecția';

  @override
  String get onbLater => 'Mai târziu';

  @override
  String get tabHome => 'Acasă';

  @override
  String get tabAssistant => 'Asistent';

  @override
  String get tabHistory => 'Istoric';

  @override
  String get tabSettings => 'Setări';

  @override
  String get protectionOn => 'Protecția este activă';

  @override
  String get protectionOff => 'Activează protecția';

  @override
  String get protectionOnHint => 'Vă avertizăm despre apelurile suspecte';

  @override
  String get protectionOffHint => 'Apăsați pentru a activa';

  @override
  String get protectionOffTitle => 'Cum dezactivați protecția';

  @override
  String get protectionOffBody =>
      'Protecția poate fi dezactivată doar din setările telefonului.';

  @override
  String get protectionIosTitle => 'Activați SafeCall în setări';

  @override
  String get protectionIosBody =>
      'Deschideți: Telefon → Blocare și identificare apeluri → activați SafeCall.';

  @override
  String get openSettings => 'Deschide setările';

  @override
  String dbCount(int count) {
    return 'Numere în bază: $count';
  }

  @override
  String dbUpdated(String when) {
    return 'Actualizat: $when';
  }

  @override
  String get dbNever => 'Baza nu a fost încă descărcată';

  @override
  String get justNow => 'chiar acum';

  @override
  String minutesAgo(int n) {
    return 'acum $n min';
  }

  @override
  String hoursAgo(int n) {
    return 'acum $n h';
  }

  @override
  String daysAgo(int n) {
    return 'acum $n zile';
  }

  @override
  String get updateNow => 'Actualizează acum';

  @override
  String get updating => 'Se actualizează…';

  @override
  String get assistantButton => 'Asistent AI';

  @override
  String get assistantButtonHint => 'Cereți un sfat dacă aveți îndoieli';

  @override
  String get recentCalls => 'Apeluri recente';

  @override
  String get allHistory => 'Tot istoricul';

  @override
  String get noCalls => 'Nu au fost încă apeluri verificate';

  @override
  String get manualCheck => 'Verificați un număr manual';

  @override
  String get phoneHint => '+373 69 123 456';

  @override
  String get checkButton => 'Verifică';

  @override
  String reportsCount(int n) {
    return 'Plângeri: $n';
  }

  @override
  String schemeLabel(String name) {
    return 'Schemă: $name';
  }

  @override
  String get fromLocalDb => 'Fără conexiune — răspuns din baza de pe telefon';

  @override
  String get reportNumber => 'Raportează numărul';

  @override
  String get assistantTitle => 'Asistent AI';

  @override
  String get newChat => 'Chat nou';

  @override
  String get assistantWelcome =>
      'Bună ziua! Spuneți ce s-a întâmplat sau alegeți o întrebare de mai jos.';

  @override
  String get typing => 'Scrie…';

  @override
  String get messageHint => 'Scrieți o întrebare';

  @override
  String get send => 'Trimite';

  @override
  String get chipBank => 'Mă sună de la bancă';

  @override
  String get chipCode => 'Am spus codul din SMS';

  @override
  String get chipUnknown => 'Ce înseamnă ⚪ Număr necunoscut?';

  @override
  String get chipTransfer => 'Ce fac dacă am transferat deja bani?';

  @override
  String get assistantDisclaimer =>
      'Asistentul oferă sfaturi generale. În caz de îndoială, sunați la bancă la numărul de pe card sau la 112.';

  @override
  String get reportTitle => 'Raportați apelul';

  @override
  String get reportQuestion => 'A fost un apel suspect?';

  @override
  String get reportWhat => 'Ce s-a întâmplat? Bifați tot ce a fost';

  @override
  String get optBank => 'S-au prezentat de la bancă';

  @override
  String get optPolice => 'S-au prezentat de la poliție';

  @override
  String get optOtp => 'Au cerut codul din SMS';

  @override
  String get optCard => 'Au cerut datele cardului';

  @override
  String get optTransfer => 'Au cerut să transferați bani';

  @override
  String get optApp => 'Au propus să instalați o aplicație';

  @override
  String get optOther => 'Altceva';

  @override
  String get tellMore => 'Povestiți ce s-a întâmplat';

  @override
  String get tellMoreHint => 'Opțional. Textul nu este salvat';

  @override
  String get reportSend => 'Trimite';

  @override
  String get thanksTitle => 'Mulțumim, i-ați ajutat pe alții';

  @override
  String get thanksBody =>
      'Semnalul dvs. va ajuta la avertizarea altor oameni la timp.';

  @override
  String get thanksQueued =>
      'Acum nu există conexiune — vom trimite mesajul când va apărea internetul.';

  @override
  String get historyTitle => 'Istoricul apelurilor';

  @override
  String get historyEmpty => 'Aici vor apărea apelurile verificate de SafeCall';

  @override
  String get reportAction => 'Raportează';

  @override
  String get reportedLabel => 'Trimis';

  @override
  String get settingsTitle => 'Setări';

  @override
  String get sectionAbout => 'Despre SafeCall';

  @override
  String get howItWorks => 'Cum funcționează';

  @override
  String get howItWorksBody =>
      'Când sunteți apelat, SafeCall primește doar numărul apelantului.\n\nNumărul este verificat într-o bază păstrată pe telefonul dvs. Nu este nevoie de internet, așa că răspunsul vine într-o fracțiune de secundă.\n\nDacă alți oameni s-au plâns de acest număr, veți vedea un avertisment. Apelul nu este blocat — dvs. decideți dacă răspundeți.\n\nDupă apel puteți spune dacă a fost suspect. Așa baza devine mai precisă pentru toți.';

  @override
  String get privacy => 'Confidențialitate';

  @override
  String get privacyStored => 'Ce se păstrează';

  @override
  String get privacyStoredBody =>
      'Baza de numere cu nivelul de risc și istoricul apelurilor verificate (număr, oră, stare) — doar pe telefonul dvs. Pentru legătura cu serverul se folosește un cod aleatoriu al dispozitivului.';

  @override
  String get privacyNotStored => 'Ce nu se păstrează';

  @override
  String get privacyNotStoredBody =>
      'Sunetul convorbirilor, contactele, numele și numărul dvs. Conversația cu asistentul nu este salvată și se șterge cu butonul «Chat nou». Textul plângerii este folosit doar pentru recunoașterea schemei și nu este păstrat.';

  @override
  String get sectionDatabase => 'Baza de numere';

  @override
  String get updateDb => 'Actualizează baza acum';

  @override
  String get sectionNotifications => 'Notificări';

  @override
  String get notifications => 'Avertismente despre apeluri';

  @override
  String get language => 'Limba';

  @override
  String get langRu => 'Русский';

  @override
  String get langRo => 'Română';

  @override
  String get version => 'Versiune';

  @override
  String get server => 'Adresa serverului';

  @override
  String get serverHint =>
      'Pentru iPhone — IP-ul calculatorului din aceeași rețea Wi-Fi';

  @override
  String get save => 'Salvează';

  @override
  String get resetDefault => 'Implicit';

  @override
  String get sectionDemo => 'Pentru demo';

  @override
  String get simulateCall => 'Simulează un apel';

  @override
  String get simulateTitle => 'Simulare apel';

  @override
  String get simulateHint =>
      'Introduceți un număr sau alegeți un exemplu. Aplicația îl verifică la fel ca la un apel real: escroc din bază — avertisment imediat, orice număr — întrebare după apel.';

  @override
  String get channelWarnings => 'Avertismente despre apeluri';

  @override
  String get channelReports => 'Întrebări după apel';

  @override
  String get channelSync => 'Actualizarea bazei';

  @override
  String get callerIdHigh => '⚠️ SafeCall: posibilă fraudă';

  @override
  String get callerIdMedium => '⚠️ SafeCall: fiți atenți';

  @override
  String get notifScamTitle => 'Atenție, posibil v-a sunat un escroc';

  @override
  String get postCallScamBody => 'Apăsați dacă a fost un escroc';

  @override
  String get postCallUnknownBody =>
      'A fost un escroc? Apăsați pentru a raporta';

  @override
  String get actionScam => '❗ Este escroc';

  @override
  String get actionYesScam => '❗ Da, escroc';

  @override
  String get quickReportSending => 'Trimitem numărul…';

  @override
  String get simulateInCall => 'Apel în curs…';

  @override
  String get simulateEnd => 'Încheie apelul';

  @override
  String get simulateEnded => 'Apel încheiat — vedeți notificarea';

  @override
  String get simulateScamPreset => 'Escroc din bază';

  @override
  String get simulateUnknownPreset => 'Număr nou';

  @override
  String get simulateCallButton => 'Sună';
}
