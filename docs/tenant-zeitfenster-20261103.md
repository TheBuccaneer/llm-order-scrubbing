# Getrennte Benutzersalts bei unbekannter A-Startzeit

Stand: 03.11.2026. Entscheidungstest nach dem Audit des
[synchronisierten Zwei-Benutzer-Piloten](getrennte-salts-scheduler-20261103.md).
Alle Anfragen gingen ausschließlich an den eigenen lokalen
Qwen2.5-7B-Instruct/vLLM-0.17.1-Server auf der RTX 3090.

## Frage und Abgrenzung

Kann B den Cachezustand einer **bekannten, identischen**
Dokument-A-Zielanfrage von A noch aus Bs eigenen vollständigen
Antwortzeiten erkennen, wenn B den genauen Startzeitpunkt von A
nicht kennt? A und B besitzen verschiedene, über alle Messfälle
hinweg unveränderte 256-Bit-Cache-Salts. Bs vier Dokument-Prompts
bleiben ebenfalls unverändert. Diese Kontrolle entfernt den
`Case NNN`-Promptunterschied des früheren festen-Salt-Versuchs.

Die Forschungsgrenze ist eng: Die [aktuelle vLLM-
Sicherheitsdokumentation](https://docs.vllm.ai/en/latest/usage/security/)
weist ausdrücklich darauf hin, dass `cache_salt` einzelne
Cache-Risiken senkt, aber keine vollständige Mandantenisolation
eines gemeinsam geplanten Serverprozesses ist. Das ist eine
aktuelle allgemeine Produktaussage, nicht die Beschreibung
unserer gemessenen vLLM-Version. [FairInference v1,
§§2.1–2.2 und 7.1.1](https://arxiv.org/html/2609.18112)
untersucht bereits LLM-Interferenz und unterschiedliche
Präfixtreffer als Leistungsproblem; wir prüfen die konkrete
Vertraulichkeitsinferenz aus Bs vollständigen Antworten.
[Abu Bakar v1, §§IV und XV](https://arxiv.org/html/2609.06853)
betont die Abhängigkeit von Überlappung und Konkurrenz.
Dieser Versuch bleibt ein ruhiger, absichtlich überlappender
Loopback-Pilot, kein allgemeiner Produktionsnachweis. Die
vorherige Quellenkarte bleibt in `docs/quellen.md` erhalten.

## Vorab festgelegter Test

[Protokoll](../results/tenant-offset-20261103/protocol.json),
[Fallfolge](../results/tenant-offset-20261103/cases.json),
Salts und Angreifer standen in Commit `98accc6` **vor**
der Messung fest. Acht gepaarte Warm/Kalt-Fälle nutzen je
denselben B-Sendeplan und denselben A-Startversatz. Die
Versätze 0, 150, 300 und 450 ms kommen je zweimal vor;
ihre Reihenfolge und Warm/Kalt innerhalb jedes Paares wurden
vorher randomisiert. Vier Fälle ohne A-Zielanfrage und vier
mit einer **anderen kalten A-Anfrage** sind eingestreute
Kontrollen. B kennt das Fenster, nicht den tatsächlichen
Versatz. Seine vier eigenen Anfragen starten nominell bei
0/10/20/30 ms.

A schickt vor jedem Fall genau eine 548-Token-
Ein-Token-Vorbereitungsanfrage: Dokument A für warm,
Dokument D für kalt. Nach 250 ms Ruhe folgt in beiden
Hauptbedingungen dieselbe Dokument-A-Zielanfrage mit
548 Prompt- und 16 Ausgabetokens. Die andere kalte Kontrolle
bereitet A vor und sendet dann Dokument D; die Kontrolle
ohne Zielanfrage bereitet D vor. Die beiden festen Salts
werden über alle 24 Fälle wiederverwendet. **Jeder Fall
erhält einen frischen Backend-Start**, damit frühere
Zielanfragen mit dem festen A-Salt den nächsten kalten
Fall nicht aufwärmen. Die Fallfolge hatte vier warme und
vier kalte Erstfälle in den Paaren.

Die Angreiferregel wurde ausschließlich aus den alten
16 Entwicklungsfällen mit **genau denselben 548-Token-
Dokument-Prompts** trainiert, also vor diesem Test.
T1 verwendet den ersten vollständigen B-Empfang relativ
zu Bs erstem eigenen Versand, T2 alle vier B-Empfangszeiten,
R2 nur Bs Antwortreihenfolge. Die logistische Modellklasse
(`StandardScaler`, `C=1`) und die Richtung „warm früher“
blieben unverändert. A-Timestamps, A-Salt, Cachezähler und
Proxy-/Backendlogs waren keine Angreifermerkmale. Das
vorab fixierte Erfolgskriterium war gültige Cachetrennung
und Überlappung plus mindestens 7/8 gepaarte T1-Unterschiede
in der alten Richtung oder T1-AUC mindestens 0,75 bei
mindestens 12/16 T1-Klassifikationen.

## Integrität und Ergebnis

Alle **24 Backend-Starts**, 24 Vorbereitungen, 20
A-Zielanfragen und **96 vollständigen B-Antworten** waren
vorhanden; die gespeicherte Integritätsprüfung meldete
keinen Fehler. As warme Zielanfragen meldeten 8/8 Mal
544 gecachte Tokens, As kalte 8/8 Mal keinen Treffer.
Bei B meldete keine der 96 Probes einen Cachetreffer;
das Diagnosefeld war aus ihren Clientantworten entfernt.
Alle 16 Haupt-Zielanfragen und die vier anderen kalten
Kontrollen überlappten mindestens eine laufende B-Anfrage.
Die tatsächlich gemessenen A-Startversätze lagen sehr nahe
bei den geplanten 0/150/300/450 ms (−0,33 bis 450,36 ms
insgesamt; minimale negative Werte entstehen aus der
gleichzeitigen Thread-Freigabe bei 0 ms).

| Nur B-Clientdaten, 8 warm / 8 kalt | Ergebnis |
| --- | ---: |
| T1, erster vollständiger B-Empfang | **14/16** (Wilson 95 %: 64,0–96,5 %) |
| T2, vier vollständige B-Zeiten | **16/16** (80,6–100 %) |
| R2, nur B-Reihenfolge | 8/16 |
| T1-Rang-AUC, Richtung aus alten Entwicklungsdaten | **1,000** (8 gegen 8) |
| Gepaarte Warm/Kalt-Differenz in alter Richtung | **8/8** (Wilson 67,6–100 %; einseitiger Vorzeichentest `p=0,003906`) |

Die exakte einseitige Mann-Whitney-Wahrscheinlichkeit für die
beobachtete T1-Rangtrennung beträgt 0,0000777, setzt aber
unabhängige Beobachtungen voraus. Für das gepaarte Design
ist der Vorzeichentest die vorsichtigere primäre
Unsicherheitsangabe. Die acht gepaarten Unterschiede
„kalt minus warm“ lagen bei 71,2 bis 146,0 ms;
je Versatz gab es nur zwei Paare. Die alte absolute
T1-Kalibrierung verfehlte zwei kalte Fälle bei 0 ms,
obwohl die relative AUC 1,0 war. Eine neue Schwelle wurde
nicht angepasst. T2 traf beide Fälle; es ist ein
sekundärer, ebenfalls vorher trainierter Beobachter.

Die Mediane von Bs erster vollständiger Antwort waren
934,6 ms für warm und 1065,6 ms für kalt. Die
Kontrollen erklären die Reichweite des Befunds:
ohne A-Zielanfrage lag der Median bei 931,3 ms und
der alte T1/T2-Klassifikator nannte alle vier Fälle
„warm“. Mit einer **anderen kalten** A-Zielanfrage
lag er bei 1063,9 ms und alle vier wurden „kalt“
genannt. Diese je vier Fälle beweisen keine Gleichheit
der Verteilungen; sie zeigen aber, dass der Beobachter
in diesem Aufbau vor allem die konkurrierende
Rechenarbeit sieht. Er identifiziert **nicht** aus sich
heraus den konkreten Dokumentzugriff oder As Anwesenheit.

## Wissenschaftliche Entscheidung

Die wichtigste Auditkritik zur exakten 15-ms-Synchronisierung
ist für dieses begrenzte Fenster **nicht** der Grund des
früheren starken Signals: Der vorab eingefrorene Angriff
trennt warm/kalt auch bei verborgenen Startlagen bis 450 ms.
Die zweite Kritik ist hier unmittelbar beseitigt: fester
Benutzersalt, identischer A-Zielprompt in beiden Zuständen,
keine öffentlichen Fallcodes und ein frischer Backend-Start
je Messfall. Das erfüllt die vorab festgelegte
Entscheidungshilfe.

Die **Anwendungsgrenze bleibt entscheidend**. B weiß im
Hauptvergleich, dass A innerhalb eines bekannten 450-ms-
Fensters genau die bekannte Dokument-A-Zielanfrage stellt;
alle Hauptfälle überlappen tatsächlich B. Die Kontrollen
zeigen, dass beliebige andere kalte Arbeit ähnlich aussieht
und Abwesenheit ähnlich wie ein warmer A-Fall. Daraus folgt
kein Angriff, der ohne weitere Kontextinformation erkennt,
*welches* Dokument ein unbekannter anderer Benutzer gerade
öffnet. Der Befund ist eine konditionale Inferenz des
Cachezustands beziehungsweise der Rechenlast einer
bekannten A-Anfrage bei getrennten Cache-Namensräumen.

Für das ICCAI-2027-Paper ist dies ein stärkerer,
reproduzierbarer **Threat-Model- und Evaluationsbefund**:
Salt-getrennte KV-Wiederverwendung allein eliminiert die
beobachtbare Kopplung durch gemeinsame Ausführung nicht.
Interferenz und per-tenant Latenzisolation sind bereits
bekannt; eine allgemeine neue Side-Channel-Klasse oder
eine neue Schutzmethode ist damit nicht belegt.
Bevor eine tenantbewusste Zulassungs-/Freigaberegel als
eigener Beitrag entwickelt wird, sollte die Anwendung
explizit sagen, welche Information B über As Zielanfrage
und Zeitfenster realistisch besitzt. Ein späterer
Schutzvergleich muss direkte Freigabe, BOS, einen festen
Slot und eine stärkere Isolationsbaseline bei gleichem
Latenzbudget bewerten. Das bisherige empirische Paper
bleibt die belastbare Ausgangsbasis; eine große
Messkampagne folgt aus diesem Pilot nicht automatisch.

## Reproduktion und Daten

Unter `results/tenant-offset-20261103/` liegen
`protocol.json`, `cases.json`, die **synthetischen**
`salts.json`, 24 unveränderte Fallordner mit
`trial.json`, `proxy.jsonl` sowie Client-, Proxy- und
Serverlog, und `analysis.json`. Der Lauf verwendet
`src/tenant_offset_case.py` und `run.sh`; die
Auswertung `src/tenant_offset_analysis.py` liest
für das Training nur
`results/tenant-scheduler-20261103/dev/trials.jsonl`.
Keine alte Rohdatei wurde geändert. Die lokalen
Server und Proxies wurden nach jedem Fall beendet;
kein Push.
