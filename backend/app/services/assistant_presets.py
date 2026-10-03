"""Ready-made assistant phrases shown as buttons, and the vetted answers behind them.

A button press sends its text as a normal chat message. When the text matches a button, the answer
below is returned at once, without calling Gemini: it is instant, identical for everyone, works with
no key or when the model is down, and the most critical advice ("I already told the code") is never
left to a model's improvisation. The same topics serve as a keyword fallback when Gemini fails.

The first four buttons are the app's built-in chips (mobile/lib/l10n/app_*.arb: chipBank, chipCode,
chipUnknown, chipTransfer); keep their texts in sync.
"""

import re
from dataclasses import dataclass, field

LANGS = ("ru", "ro")


@dataclass(frozen=True)
class Preset:
    id: str
    button: dict[str, str]
    answer: dict[str, str]
    follow_ups: tuple[str, ...]
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = field(default=())  # extra phrasings that count as the button


PRESETS: tuple[Preset, ...] = (
    Preset(
        id="bank_call",
        button={"ru": "Мне звонят из банка", "ro": "Mă sună de la bancă"},
        answer={
            "ru": (
                "Если «банк» звонит сам и говорит о подозрительной операции, блокировке карты или «защите счёта», "
                "скорее всего, это мошенники.\n"
                "1. Положите трубку. Ничего не подтверждайте.\n"
                "2. Не называйте коды из SMS, номер карты, CVV и PIN.\n"
                "3. Сами позвоните в банк по номеру на обратной стороне карты и спросите, была ли проблема.\n"
                "Настоящий банк никогда не просит коды из SMS, перевод на «безопасный счёт» или установку приложений."
            ),
            "ro": (
                "Dacă „banca” vă sună singură și vorbește despre o operațiune suspectă, blocarea cardului sau "
                "„protejarea contului”, cel mai probabil sunt escroci.\n"
                "1. Închideți apelul. Nu confirmați nimic.\n"
                "2. Nu spuneți codurile din SMS, numărul cardului, CVV-ul sau PIN-ul.\n"
                "3. Sunați chiar dumneavoastră la bancă, la numărul de pe spatele cardului, și întrebați dacă a fost "
                "o problemă.\n"
                "O bancă adevărată nu cere niciodată coduri din SMS, transfer într-un „cont sigur” sau instalarea "
                "de aplicații."
            ),
        },
        follow_ups=("code_shared", "install_app", "how_report"),
        keywords=("банк", "banc"),
        aliases=("мне звонили из банка", "звонят из банка", "mă sună banca", "m-a sunat banca"),
    ),
    Preset(
        id="code_shared",
        button={"ru": "Я сообщил(а) код из SMS", "ro": "Am spus codul din SMS"},
        answer={
            "ru": (
                "Действуйте сразу, каждая минута важна:\n"
                "1. Позвоните в банк по номеру на обратной стороне карты и скажите, что сообщили код мошенникам.\n"
                "2. Попросите заблокировать карту или заблокируйте её сами в приложении банка.\n"
                "3. Если пропали деньги, позвоните в полицию по номеру 112.\n"
                "4. Сохраните доказательства: номер звонившего, время звонка, SMS и скриншоты.\n"
                "Больше никому не называйте коды, даже если звонят «из банка» или «из полиции»."
            ),
            "ro": (
                "Acționați imediat, fiecare minut contează:\n"
                "1. Sunați la bancă la numărul de pe spatele cardului și spuneți că ați dat codul unor escroci.\n"
                "2. Cereți blocarea cardului sau blocați-l singur în aplicația băncii.\n"
                "3. Dacă au dispărut bani, sunați la poliție la 112.\n"
                "4. Păstrați dovezile: numărul apelantului, ora apelului, SMS-urile și capturile de ecran.\n"
                "Nu mai spuneți nimănui codurile, chiar dacă vă sună „de la bancă” sau „de la poliție”."
            ),
        },
        follow_ups=("money_sent", "how_report", "bank_call"),
        aliases=("я сообщил код из sms", "я сообщила код из sms", "я назвал код", "я назвала код", "am dat codul"),
    ),
    Preset(
        id="unknown_status",
        button={"ru": "Что значит ⚪ Неизвестный номер?", "ro": "Ce înseamnă ⚪ Număr necunoscut?"},
        answer={
            "ru": (
                "«Неизвестный номер» значит, что жалоб на него в нашей базе пока нет. Это не значит, что номер "
                "безопасный.\n"
                "Если звонящий просит код из SMS, данные карты, перевод денег или установить приложение, положите "
                "трубку и перезвоните в организацию сами по официальному номеру."
            ),
            "ro": (
                "„Număr necunoscut” înseamnă că încă nu avem plângeri despre el în baza noastră. Asta nu înseamnă că "
                "numărul este sigur.\n"
                "Dacă apelantul cere codul din SMS, datele cardului, un transfer de bani sau instalarea unei "
                "aplicații, închideți și sunați chiar dumneavoastră instituția la numărul oficial."
            ),
        },
        follow_ups=("statuses", "how_report", "bank_call"),
        keywords=("неизвестн", "necunoscut"),
    ),
    Preset(
        id="money_sent",
        button={"ru": "Что делать, если я уже перевёл деньги?", "ro": "Ce fac dacă am transferat deja bani?"},
        answer={
            "ru": (
                "Не теряйте времени:\n"
                "1. Сразу позвоните в банк по номеру на карте и попросите остановить или оспорить перевод.\n"
                "2. Заблокируйте карту.\n"
                "3. Позвоните в полицию по номеру 112 и напишите заявление.\n"
                "4. Сохраните всё: номер звонившего, время, куда переводили деньги, SMS и скриншоты.\n"
                "Чем быстрее вы обратитесь в банк, тем больше шансов вернуть деньги. Если потом позвонят и предложат "
                "«вернуть деньги» за плату, это тоже мошенники."
            ),
            "ro": (
                "Nu pierdeți timpul:\n"
                "1. Sunați imediat la bancă la numărul de pe card și cereți oprirea sau contestarea transferului.\n"
                "2. Blocați cardul.\n"
                "3. Sunați la poliție la 112 și depuneți o plângere.\n"
                "4. Păstrați totul: numărul apelantului, ora, contul în care ați transferat, SMS-urile și capturile "
                "de ecran.\n"
                "Cu cât vă adresați mai repede băncii, cu atât sunt mai mari șansele să recuperați banii. Dacă vă sună "
                "cineva și vă oferă să „recuperați banii” contra cost, sunt tot escroci."
            ),
        },
        follow_ups=("code_shared", "how_report"),
        aliases=("я уже перевел деньги", "я уже перевела деньги", "что делать если я уже перевела деньги"),
    ),
    Preset(
        id="police_call",
        button={"ru": "Мне звонят из полиции", "ro": "Mă sună de la poliție"},
        answer={
            "ru": (
                "Полиция не решает дела по телефону: не просит перевести деньги, «задекларировать сбережения», "
                "назвать код из SMS или никому не рассказывать о звонке.\n"
                "1. Положите трубку.\n"
                "2. Если волнуетесь, сами позвоните по номеру 112 и спросите, есть ли к вам вопросы.\n"
                "3. Не переводите деньги и не передавайте их курьеру."
            ),
            "ro": (
                "Poliția nu rezolvă cazuri la telefon: nu cere transferul banilor, „declararea economiilor”, codul din "
                "SMS și nici să nu spuneți nimănui despre apel.\n"
                "1. Închideți apelul.\n"
                "2. Dacă sunteți îngrijorat, sunați chiar dumneavoastră la 112 și întrebați dacă aveți vreo problemă.\n"
                "3. Nu transferați bani și nu-i dați unui curier."
            ),
        },
        follow_ups=("relative", "money_sent", "how_report"),
        keywords=("полиц", "следовател", "прокурат", "poliți", "politi", "procuror", "anchetator"),
    ),
    Preset(
        id="install_app",
        button={"ru": "Просят установить приложение", "ro": "Mi se cere să instalez o aplicație"},
        answer={
            "ru": (
                "Не устанавливайте. Программы вроде AnyDesk, TeamViewer или «защиты от банка» дают мошенникам "
                "управление вашим телефоном и доступ к банку.\n"
                "Если уже установили:\n"
                "1. Удалите приложение.\n"
                "2. Позвоните в банк по номеру на карте и попросите проверить счёт и заблокировать карту.\n"
                "3. Смените пароль от приложения банка."
            ),
            "ro": (
                "Nu instalați nimic. Programe precum AnyDesk, TeamViewer sau „protecție de la bancă” le dau escrocilor "
                "controlul telefonului și acces la bancă.\n"
                "Dacă ați instalat deja:\n"
                "1. Ștergeți aplicația.\n"
                "2. Sunați la bancă la numărul de pe card și cereți verificarea contului și blocarea cardului.\n"
                "3. Schimbați parola aplicației băncii."
            ),
        },
        follow_ups=("code_shared", "money_sent"),
        keywords=(
            "установ", "приложен", "anydesk", "teamviewer", "rustdesk", "удаленн", "instal", "aplicați", "aplicati",
        ),
    ),
    Preset(
        id="relative",
        button={"ru": "Звонят от имени родственника", "ro": "Sună în numele unei rude"},
        answer={
            "ru": (
                "Это похоже на схему «родственник в беде»: говорят, что сын или внук попал в аварию или в полицию, "
                "и срочно нужны деньги.\n"
                "1. Положите трубку.\n"
                "2. Сами позвоните родственнику по его обычному номеру.\n"
                "3. Не передавайте деньги курьеру и не переводите их, пока не поговорите с родными."
            ),
            "ro": (
                "Seamănă cu schema „ruda în necaz”: vi se spune că fiul sau nepotul a făcut un accident sau a ajuns "
                "la poliție și are nevoie urgentă de bani.\n"
                "1. Închideți apelul.\n"
                "2. Sunați chiar dumneavoastră ruda la numărul ei obișnuit.\n"
                "3. Nu dați bani unui curier și nu transferați nimic până nu vorbiți cu ai dumneavoastră."
            ),
        },
        follow_ups=("police_call", "money_sent"),
        keywords=(
            "родствен", "внук", "сын ", "дочь", "дочка", "авари", "rudă", "rude", "nepot", "fiul", "fiica", "accident",
        ),
    ),
    Preset(
        id="statuses",
        button={"ru": "Что значат статусы номеров?", "ro": "Ce înseamnă stările numerelor?"},
        answer={
            "ru": (
                "SafeCall показывает, что известно о номере:\n"
                "• «Опасно»: много похожих жалоб, лучше не отвечать.\n"
                "• «Осторожно»: есть жалобы или признаки известной мошеннической схемы.\n"
                "• «Мало жалоб»: на номер жаловались редко.\n"
                "• «Неизвестный номер»: данных пока нет, это не значит, что номер безопасный.\n"
                "Звонок никогда не блокируется: отвечать или нет, решаете вы."
            ),
            "ro": (
                "SafeCall arată ce se știe despre număr:\n"
                "• „Pericol”: multe plângeri asemănătoare, mai bine nu răspundeți.\n"
                "• „Atenție”: există plângeri sau semne ale unei scheme de fraudă cunoscute.\n"
                "• „Puține plângeri”: numărul a fost raportat rar.\n"
                "• „Număr necunoscut”: încă nu avem date, asta nu înseamnă că numărul este sigur.\n"
                "Apelul nu este blocat niciodată: dumneavoastră decideți dacă răspundeți."
            ),
        },
        follow_ups=("unknown_status", "how_report"),
        keywords=("статус", "цвет", "опасно", "осторожно", "stare", "stări", "culoare", "pericol"),
    ),
    Preset(
        id="how_report",
        button={"ru": "Как пожаловаться на номер?", "ro": "Cum raportez un număr?"},
        answer={
            "ru": (
                "После подозрительного звонка SafeCall пришлёт уведомление: нажмите на него и отметьте, что "
                "произошло. Можно и позже: откройте «Историю звонков» и нажмите «Сообщить» рядом с номером.\n"
                "Жалоба анонимная: мы не сохраняем ваше имя, контакты и запись разговора. Каждая жалоба помогает "
                "предупредить других."
            ),
            "ro": (
                "După un apel suspect, SafeCall vă trimite o notificare: apăsați pe ea și bifați ce s-a întâmplat. "
                "Puteți și mai târziu: deschideți „Istoricul apelurilor” și apăsați „Raportează” lângă număr.\n"
                "Raportarea este anonimă: nu păstrăm numele, contactele sau înregistrarea convorbirii. Fiecare "
                "raportare îi ajută pe alții să fie avertizați."
            ),
        },
        follow_ups=("statuses", "bank_call"),
        keywords=("пожаловат", "жалоб", "сообщить о номер", "raport", "plâng", "reclam"),
    ),
)

BY_ID = {p.id: p for p in PRESETS}
DEFAULT_SUGGESTIONS = tuple(p.id for p in PRESETS)
DEFAULT_FOLLOW_UPS = ("code_shared", "money_sent", "how_report")

FALLBACK = {
    "ru": (
        "Сейчас не получается ответить подробно, но вот главное:\n"
        "1. Банк и полиция никогда не просят коды из SMS, данные карты, перевод на «безопасный счёт» и установку "
        "приложений.\n"
        "2. Если сомневаетесь, положите трубку и перезвоните сами по официальному номеру.\n"
        "3. Если уже сообщили код или перевели деньги, сразу позвоните в банк по номеру на карте и в полицию по 112."
    ),
    "ro": (
        "Acum nu pot răspunde în detaliu, dar iată esențialul:\n"
        "1. Banca și poliția nu cer niciodată coduri din SMS, datele cardului, transfer într-un „cont sigur” sau "
        "instalarea de aplicații.\n"
        "2. Dacă aveți dubii, închideți și sunați chiar dumneavoastră la numărul oficial.\n"
        "3. Dacă ați spus deja codul sau ați transferat bani, sunați imediat la bancă la numărul de pe card și la "
        "poliție la 112."
    ),
}

# --------------------------------------------------------------------------- matching

_ROMANIAN_LETTERS = set("ăâîșşțţ")
_CODE_WORDS = ("код", "cod")
_DISCLOSED = (
    "сообщил", "назвал", "продиктовал", "сказал", "отправил", "ввел", "ввёл", "переслал",
    "am spus", "am dat", "am trimis", "am comunicat", "am introdus",
)
_MONEY_SENT = (
    "перевел", "перевёл", "отправил деньги", "отдал деньги", "передал деньги", "сняли деньги", "списали",
    "am transferat", "am trimis bani", "am dat bani", "am plătit", "am platit",
)


def normalize(text: str) -> str:
    """Case, ё/е, gender endings like "сообщил(а)", punctuation and emoji do not matter."""
    t = text.lower().replace("ё", "е").replace("ş", "ș").replace("ţ", "ț")
    t = re.sub(r"\(а\)", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def detect_language(text: str) -> str:
    lowered = text.lower()
    if _ROMANIAN_LETTERS & set(lowered):
        return "ro"
    latin = sum(1 for c in lowered if "a" <= c <= "z")
    cyrillic = sum(1 for c in lowered if "а" <= c <= "я" or c == "ё")
    return "ro" if latin > cyrillic else "ru"


_BUTTON_INDEX: dict[str, tuple[Preset, str]] = {}
for _preset in PRESETS:
    for _lang, _text in _preset.button.items():
        _BUTTON_INDEX[normalize(_text)] = (_preset, _lang)
    for _alias in _preset.aliases:
        _BUTTON_INDEX[normalize(_alias)] = (_preset, detect_language(_alias))


def match_button(text: str) -> tuple[Preset, str] | None:
    """The preset whose button (or alias) this message is, with the button's language."""
    return _BUTTON_INDEX.get(normalize(text))


_TOPIC_ORDER = ("install_app", "police_call", "relative", "bank_call", "unknown_status", "statuses", "how_report")


def match_topic(text: str) -> Preset | None:
    """Best-effort topic from keywords; the most urgent situations win."""
    t = " " + text.lower().replace("ё", "е") + " "
    if any(w in t for w in _CODE_WORDS) and any(w in t for w in _DISCLOSED):
        return BY_ID["code_shared"]
    if any(w in t for w in _MONEY_SENT):
        return BY_ID["money_sent"]
    for preset_id in _TOPIC_ORDER:
        if any(k in t for k in BY_ID[preset_id].keywords):
            return BY_ID[preset_id]
    return None


def buttons(ids: tuple[str, ...], lang: str) -> list[str]:
    return [BY_ID[i].button[lang] for i in ids if i in BY_ID]
