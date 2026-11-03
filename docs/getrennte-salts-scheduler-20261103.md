# Zwei Benutzer, getrennte Cache-Salts, gemeinsamer Scheduler

Stand: 03.11.2026. Gezielter lokaler Pilot für einen synthetischen
Mehrbenutzer-Assistenten zur Dokumentenanalyse. Alle Anfragen gingen
an den eigenen Qwen2.5-7B-Instruct/vLLM-0.17.1-Server auf der RTX 3090.
Es wurde kein fremder Dienst verwendet und keine neue Schutzregel gebaut.

**Audit-Fortsetzung:** Der anschließend vorab festgelegte
[Test mit verborgener A-Startzeit](tenant-zeitfenster-20261103.md)
verwendet feste Benutzersalts, identische Zielprompts und
frische Backends je Fall. Er bestätigt den konditionalen
Warm/Kalt-Zeitkanal bis 450 ms Startversatz, zeigt mit
Kontrollen aber auch, dass der Beobachter andere kalte
Arbeit und Abwesenheit nicht dokumentenspezifisch trennt.
Die untenstehende Empfehlung für einen Schutzvergleich ist
deshalb an ein ausdrücklich definiertes Anwendungswissen
über As Zielanfrage zu binden.

## Frage und Literaturgrenze

Kann Benutzer B aus **eigenen vollständigen Antwortzeiten** erkennen,
ob eine zeitlich bekannte Dokumentenanfrage von A unter dessen
eigenem, für B nicht wiederverwendbarem Salt einen KV-Cachetreffer
hatte? Das ist enger als eine allgemeine Rekonstruktion fremder
Dokumente. Das zu erratende Bit ist der Cachezustand vor As
bekannter Zielanfrage, nicht As bloße Anwesenheit: In beiden
Bedingungen sendet A gleich viele Anfragen mit gleicher Tokenzahl
und derselben geplanten Ankunftsstruktur.

[vLLM 0.17.1](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/)
hashiert den Salt im ersten Cacheblock; gleiche Tokens mit
verschiedenen Salts dürfen daher keinen Cacheblock teilen.
[KVGov v1, §4.1](https://arxiv.org/html/2608.09225)
untersucht diese Namespace-Isolation gegen direkte
Cachetreffer-Probes. Seine Aussage über fehlende direkte
Cache-Fingerprints widerlegt diesen Pilot nicht: B erzielt hier
**keinen** fremden Cachetreffer. [FairInference, §§2.1–2.2 und
7.1.1](https://arxiv.org/html/2609.18112) beschreibt bereits
Interferenz zwischen LLM-Benutzern, auch bei unterschiedlicher
Präfix-Wiederverwendung, als Leistungsproblem. Unser Zusatz ist
ein kontrollierter **Vertraulichkeitstest** dieser Kopplung mit
getrennten Salts und vollständigen B-Antworten. Interferenz an
sich ist also kein Neuheitsclaim. [Pacer, §3.2](https://www.usenix.org/system/files/sec22-mehta.pdf)
fordert einen geheimnisunabhängigen tatsächlichen Sendeplan;
eine bloße feste Sollzeit mit geheimnisabhängigem Fallback genügt
nicht. [Abu Bakar 2026, §§IV, XV](https://arxiv.org/html/2609.06853)
zeigt, wie stark Cache-Timing-Befunde von Konkurrenz und
zeitlicher Überlappung abhängen. Die folgende Leerlaufmessung
ist entsprechend eine günstige, präzise kontrollierte Situation.

## Aufbau und Vorabfestlegung

A sendet vor jeder Gruppe unter **As Salt** genau eine
Ein-Token-Vorbereitungsanfrage: Dokument A für „warm“, Dokument D
für „kalt“. Nach 250 ms Pause sendet A in beiden Bedingungen
dasselbe Dokument A mit 16 Ausgabetokens. Bs Salt ist unabhängig
und bleibt ihm zugeordnet. B sendet seine vier eigenen
Dokumentenanfragen A–D in zufälliger Reihenfolge bei nominell
0/10/20/30 ms; As Zielanfrage beginnt bei 15 ms. Die
Warm/Kalt-Reihenfolge ist innerhalb jedes gepaarten B-Sendeplans
randomisiert. Vier Gruppen ohne gleichzeitige A-Zielanfrage
geben eine kleine Lastkontrolle. B erhält weder As Antwort noch
As Salt oder interne Cache-/Proxyzeiten. Die Clientfeatures
verwenden nur Bs eigene Parameter, IDs und vollständige
Sende-/Empfangszeitpunkte.

Die erste Serie nutzte **pro Gruppe neue** zufällige 256-Bit-Salts,
jeweils getrennt für A und B. Dadurch bleiben die Dokumenttexte
in Warm/Kalt-Fällen exakt gleich. Das
[Protokoll](../results/tenant-scheduler-20261103/protocol.json)
und die Angreifer standen in Commit `3f59dc2` vor dem Lauf.
Direktfreigabe: 8 gepaarte Entwicklungsfälle und 16 gepaarte
Prüffälle auf zwei Backend-Starts, je zwei beziehungsweise vier
Kontrollen. Der [BOS-Vergleich](../results/tenant-scheduler-20261103/bos-protocol.json)
stand in `ce906bd` vor zwei weiteren Starts. Die bestehende
BOS-Regel mischte **nur Bs vier fertige Antworten** zu einem
vollen W=4-Block; As Anfrage ging direkt zum selben Backend.

Weil pro Gruppe erneuerte Salts einen Dienst mit dauerhaftem
Benutzersalt nicht genau abbilden, folgte eine vorab fixierte
[Gültigkeitsprüfung](../results/tenant-scheduler-20261103/fixed-salt-protocol.json)
(Commit `9597096`). Dort behielt jeder Benutzer innerhalb jedes
Backend-Starts **einen festen, eigenen 256-Bit-Salt**. Ein
öffentlicher `Case NNN`-Code am Promptanfang hielt aufeinander
folgende Messfälle im selben Saltbereich auseinander.
[Die Tokenprüfung](../results/tenant-scheduler-20261103/fixed-token-check.json)
bestätigte vor der Messung 554 Tokens und 144 verschiedene erste
Cacheblöcke für alle 36 Fallnummern × vier Dokumente. Für
direkte Freigabe und BOS liefen jeweils neue Entwicklungs- und
Prüfstarts mit denselben balancierten Fallplänen wie zuvor,
aber neuen Salts. Diese zweite Serie verändert den öffentlichen
Code zwischen Warm/Kalt-Fällen und ist daher eine ergänzende,
nicht identische Kontrolle.

Der primäre T1-Wert ist Bs erster vollständiger Empfang relativ
zu Bs erstem eigenen Senden; T2 nutzt alle vier vollständigen
Empfangszeiten. R2 verwendet nur die Reihenfolge. Pro Modus
wurden R2/T1/T2/RT mit `StandardScaler` und logistischer
Regression (`C=1`) ausschließlich auf 16 Entwicklungsgruppen
kalibriert; die 32 Gruppen des neuen Backend-Starts blieben
unangetastet. Die Richtung des binären T1-Rangmaßes („warm
früher“) wurde ebenfalls nur aus der Entwicklung gewählt.
Die vorab festgelegte Entscheidungshilfe verlangte gültige
Cachetrennung, T1-AUC mindestens 0,75 oder T2 mindestens
24/32 sowie bei direkter Freigabe mindestens 12/16 gepaarte
Fälle in der Entwicklungsrichtung. Für die feste-Salt-Prüfung
galt diese Schwelle in beiden Modi.

## Integrität und Ergebnisse

Jede der acht Serien hatte alle geplanten Fälle: 18 Gruppen
(8 warm, 8 kalt, 2 Kontrollen) in der Entwicklung und 36
(16/16/4) in der Prüfung. Das sind insgesamt **216 Gruppen und
864 vollständige B-Antworten** über vier Bedingungen und je
zwei Backend-Starts. Alle B-Probes hatten 16 Ausgabetokens,
HTTP 200 und **keinen Cachetreffer**; das Cache-Diagnosefeld
fehlte in sämtlichen Clientantworten. As warme Zielanfrage
hatte jeweils 544 gecachte Tokens, die kalte keinen Treffer.
Alle BOS-Gruppen wurden als volle Viererblöcke freigegeben.
Die Integritätsprüfung meldete keine Fehler. Unter festen Salts
wurde pro Backend-Start genau ein A- und ein davon verschiedener
B-Salt verwendet. In allen 16 positiven Prüfgruppen je Zustand
überlappte As Zielanfrage die B-Gruppe zeitlich.

| Unabhängiger Prüfstart, je 16 warm / 16 kalt | Neue Salts je Gruppe: direkt | Neue Salts je Gruppe: BOS | Feste Benutzersalts: direkt | Feste Benutzersalts: BOS |
| --- | ---: | ---: | ---: | ---: |
| T1, binäre Accuracy | **32/32** | **32/32** | **32/32** | **32/32** |
| T2, binäre Accuracy | **32/32** | **32/32** | **32/32** | **32/32** |
| R2, nur B-Antwortreihenfolge | 16/32 | 18/32 | 16/32 | 19/32 |
| T1-AUC, warm früher als kalt | 1,000 | 1,000 | 1,000 | 1,000 |
| Gepaarte Fälle in dieser Richtung | 16/16 | 16/16 | 16/16 | 16/16 |
| Mediane erste B-Antwort, warm / kalt | 894,9 / 1011,3 ms | 973,5 / 1201,6 ms | 904,2 / 1017,8 ms | 962,4 / 1208,0 ms |
| Median gepaart kalt minus warm | 113,6 ms | 230,0 ms | 110,5 ms | 247,4 ms |
| B-Proxy-Zusatzwartezeit, Median / p95 | 0,041 / 0,075 ms | 47,9 / 191,9 ms | 0,036 / 0,073 ms | 47,2 / 193,4 ms |

Für 32/32 Accuracy reicht das Wilson-95-%-Intervall von **89,3
bis 100 %**. Für 16/16 gepaarte Richtungen reicht es von 80,6
bis 100 %; der einseitige Vorzeichentest ergibt je Prüfung
`p=0,000015`. Die Bootstrap-AUC-Intervalle kollabieren bei
perfekter Trennung der beobachteten Stichprobe auf [1, 1]; sie
sind **keine** Garantie für neue Last- oder Netzsituationen.
Mehrere Beobachter und vier lokale Prüfserien wurden betrachtet.
Die volle Trennung ist ein starker Pilotbefund, keine
modellübergreifende Fehlerratenschätzung.

Die kleinen Gruppen ohne gleichzeitige A-Zielanfrage lagen
zeitlich nahe an „warm“, nicht an „kalt“: bei festen Salts
median 887,5 ms (direkt) und 949,9 ms (BOS). Intern lag As
Vorbereitungsanfrage in beiden Zuständen bei etwa 200 ms
Median; ihre grobe Laufzeit war also vergleichbar. Die
randomisierte Paarfolge hatte 10 warme und sechs kalte
Erstfälle; verbleibende kurze Drift oder Nachwirkungen der
Vorbereitung sind damit nicht vollständig ausgeschlossen.
Intern lag As
Zielantwort im festen-Salt-Prüfteil median bei 762,2/1044,4 ms
für warm/kalt unter Direktfreigabe und 757,8/1044,5 ms unter
BOS. Bs erster Backend-Abschluss lag bei 904,0/1017,5 ms
(direkt) und 899,4/1017,8 ms (BOS). Unter BOS wartete Bs
sichtbarer Block auf seinen **letzten** Backend-Abschluss:
median 961,9/1207,4 ms. Diese interne Zeitfolge ist mit
einem gemeinsamen Scheduling-/Fertigstellungsweg vereinbar,
aber ohne instrumentierte Scheduler-Schritte kein isolierter
Beweis für eine konkrete vLLM-Entscheidung. Interne Zeiten
flossen in keinen Angreifer ein.

## Wissenschaftliche Entscheidung

**Ja: In diesem synchronisierten lokalen Szenario verrät ein
gemeinsamer Scheduler einen fremden Cachezustand trotz getrennter
Cache-Salts.** Bs eigene Probes hatten keine Cachetreffer, und
der A-Zielaufruf war in beiden Bedingungen gleich lang und
zeitlich gleich vorgesehen. Die feste-Salt-Kontrolle bestätigt,
dass der Befund nicht allein von pro Gruppe erneuerten Salts
abhängt. **BOS W=4 löst diesen Kanal hier nicht**: Es
verändert die B-Ränge, übernimmt aber den vom gemeinsamen
Backend abhängigen Zeitpunkt, an dem Bs vierte Antwort fertig
ist. Die größeren Warm/Kalt-Abstände unter BOS sind wegen
getrennter Backend-Starts deskriptiv, kein prospektiv gepaarter
Nachweis einer allgemeinen Verstärkung durch BOS.

Die mögliche ICCAI-2027-Erweiterung ist eine **neue konkrete
Evaluation und Bedrohungsgrenze**, noch keine gesicherte neue
Angriffsprimitive oder Schutzmethode. Engste Vorarbeit ist
FairInference für Mehrbenutzer-Interferenz; unser kontrolliertes
Geheimnis und der B-only-Vollantwortbeobachter machen daraus
eine prüfbare Security-Frage. KVGov und vLLM-Salts adressieren
den direkten Cachehit-Orakelweg. Eine Behauptung, Salting sei
generell wirkungslos, wäre falsch. Auch ein neu gebauter
fester Ausgabetimer wäre gegenüber Pacer und früheren
Pufferungsverfahren allein kein eigenständiger Beitrag.

**Nächster begrenzter Entscheidungstest für eine Verteidigung:**
Eine öffentlich getaktete Zulassungs- und Freigaberegel für B
mit ausdrücklich protokolliertem Spätfall gegen (a) direkt,
(b) BOS W=4 und (c) einen einfachen festen Ausgabeslot
vergleichen. Vor Implementierung sind sichtbare Ereignisse,
Latenzbudget und Fallback eindeutig festzulegen. Ein echter
Methodenbeitrag braucht weniger B-Information **bei gleichem
Kostenbudget** als diese Baselines oder eine klare neue
Unmöglichkeits-/Kosten-Grenze. Eine Alternative ist stärkere
Scheduler- oder Ressourcenisolation nach FairInference; sie
ist als bekannte, potenziell teurere Vergleichsbasis zu
behandeln. Das bisherige empirische Paper bleibt erhalten,
bis ein solcher Schutzvergleich belastbar ist. Weitere
beliebige Scheduler-Sweeps sind nicht angezeigt.

Die wichtigste Geltungsgrenze ist die feste, dem Experiment
bekannte zeitliche Nähe von A- und B-Anfragen bei lokalem
Loopback ohne fremde Last. Es gibt keine echten Benutzerkonten;
ein Messclient simuliert beide Rollen, hält die beiden Salts
und wertet aber nur B-Felder als Angriff aus. Der öffentliche
Fallcode der festen-Salt-Kontrolle ist künstlich und unterscheidet
sich zwischen Warm/Kalt-Fällen. Nur Qwen/C0, eine
Dokumentfamilie und 16 Ausgabetokens wurden gemessen.
Unbekannte Opferzeitpunkte, Last, Llama, andere Engines,
stabile Angreiferschwellen über Produktionssitzungen und eine
stärkere Schutzregel bleiben offen. Insbesondere wurden keine
realen fremden Dokumentzugriffe erkannt.

## Reproduktion

Protokolle: `results/tenant-scheduler-20261103/protocol.json`,
`bos-protocol.json`, `fixed-salt-protocol.json` und
`fixed-token-check.json`. Startskripte: `run-direct.sh`,
`run-bos.sh`, `run-fixed-salts.sh` im selben Verzeichnis.
Messclient und Auswertung: `src/tenant_scheduler_pilot.py` und
`src/tenant_scheduler_analysis.py`. Rohdaten je Serie:
`dev/`, `holdout/`, `bos/dev/`, `bos/holdout/`,
`fixed-direct/dev/`, `fixed-direct/holdout/`,
`fixed-bos/dev/`, `fixed-bos/holdout/` mit `trials.jsonl`,
`proxy.jsonl`, Client-, Proxy- und Serverlog. Die vier
`analysis.json` sind abgeleitete Auswertungen; Rohdaten wurden
nicht überschrieben. Alle Server und Proxies sind beendet.
