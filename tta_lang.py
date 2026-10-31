"""
Interface languages for TaskTriggerAntitrack (standard library only).

The program's texts are written in Spanish; _() returns them in the chosen language.
The language comes from `--lang xx` on the command line, the TTA_LANG environment
variable, or the system's interface language; anything not listed here falls back to
English. Each block below lists the texts in the order of SOURCE, one "NN|text" per line;
\\n stands for a line break and %s / %d must stay as they are.
"""
import ctypes
import locale
import os
import re
import sys

# The Spanish originals, as they appear in the code. Their position is the NN of each line.
SOURCE = [
    "Programador de tareas · terminales y alarmas",                                   # 0
    "Nombre", "Hora fija", "Aleatoria en rango", "Hora", "Desde", "hasta",              # 1-6
    "(i) La hora exacta es impredecible dentro del rango → antitrazabilidad.",          # 7
    "Repetir cada día", "Escribir en terminales", "Ejecutar programa / abrir",          # 8-10
    "Filtro (título/proceso)", "Texto a enviar", "Teclas previas", "Ventanas:",         # 11-14
    "Todas", "Primera", "Foco", "Pulsar Enter:",                                        # 15-18
    "Casa por TÍTULO o por PROCESO (p. ej. 'WindowsTerminal'); teclea el texto + Enter.",  # 19
    "Programa", "Archivo / URL", "Argumentos", "Carpeta de trabajo", "Modo ventana:",   # 20-24
    "normal", "minimizado", "oculto", "elevado",                                        # 25-28
    "Sonido", "Aviso emergente", "Mensaje del aviso",                                   # 29-31
    "Guardar tarea", "Limpiar", "Probar ahora",                                         # 32-34
    "Parte del TÍTULO o del nombre del PROCESO de las ventanas. Ej.: 'WindowsTerminal'.",  # 35
    "Lo que se teclea en cada ventana, seguido de Enter.",                              # 36
    "Teclas antes del texto. Ej.: esc  o  ctrl+c  (separa varias con espacio).",        # 37
    "Programa a ejecutar. Args/Archivo/URL se le pasan como argumentos.",               # 38
    "Archivo o URL. Sin programa, se abre con la app por defecto.",                     # 39
    "Argumentos extra, estilo línea de comandos (se respetan las comillas).",           # 40
    "Carpeta desde la que se lanza el programa.",                                       # 41
    "Tareas programadas", "Editar", "Activar / pausar", "Eliminar",                     # 42-45
    "Atajos:  Ctrl+S guardar · Ctrl+T probar · Esc limpiar · Supr eliminar",            # 46
    "Examinar…", "Cancelar",                                                            # 47-48
    "Rango inválido", "El rango 'desde/hasta' no puede ser el mismo minuto.",           # 49-50
    "Tarea guardada.", "Selecciona una tarea de la lista primero.",                     # 51-52
    "Tarea '%s' eliminada.", "tarea", "Tarea '%s' %s.", "ACTIVADA", "PAUSADA",          # 53-57
    "⏸  Pausar", "▶  Activar",                                                          # 58-59
    "Selecciona una tarea de la lista para editar.",                                    # 60
    "Editando '%s': cambia y pulsa «Guardar tarea».",                                   # 61
    "No he podido leer alarms.json:\n%s\n\n", "Lo he copiado a:\n%s\n\n",               # 62-63
    "La lista está vacía, pero el fichero NO se ha tocado. Si guardas o creas una tarea, "
    "se reescribirá: arréglalo antes o recupera la copia.",                             # 64
    "Tareas sin cargar", "PRUEBA: ", "enviado a %d ventana(s)", "programa lanzado",     # 65-68
    "Tarea «%s» disparada.",                                                            # 69
]

LANGS = {}

LANGS["en"] = """
0|Task scheduler · terminals and alarms
1|Name
2|Fixed time
3|Random in range
4|Time
5|From
6|to
7|(i) The exact time is unpredictable within the range → anti-tracking.
8|Repeat every day
9|Type into terminals
10|Run program / open
11|Filter (title/process)
12|Text to send
13|Keys before
14|Windows:
15|All
16|First
17|Focused
18|Press Enter:
19|Matches the TITLE or the PROCESS (e.g. 'WindowsTerminal'); types the text + Enter.
20|Program
21|File / URL
22|Arguments
23|Working folder
24|Window mode:
25|normal
26|minimised
27|hidden
28|elevated
29|Sound
30|Pop-up
31|Pop-up message
32|Save task
33|Clear
34|Test now
35|Part of the windows' TITLE or PROCESS name. E.g.: 'WindowsTerminal'.
36|What gets typed into each window, followed by Enter.
37|Keys before the text. E.g.: esc  or  ctrl+c  (separate several with spaces).
38|Program to run. Args/File/URL are passed to it as arguments.
39|File or URL. Without a program, it opens with the default app.
40|Extra arguments, command-line style (quotes are respected).
41|Folder the program is started from.
42|Scheduled tasks
43|Edit
44|Enable / pause
45|Delete
46|Shortcuts:  Ctrl+S save · Ctrl+T test · Esc clear · Del delete
47|Browse…
48|Cancel
49|Invalid range
50|The 'from/to' range can't be the same minute.
51|Task saved.
52|Select a task in the list first.
53|Task '%s' deleted.
54|task
55|Task '%s' %s.
56|ENABLED
57|PAUSED
58|⏸  Pause
59|▶  Enable
60|Select a task in the list to edit it.
61|Editing '%s': change it and press “Save task”.
62|Couldn't read alarms.json:\\n%s\\n\\n
63|I copied it to:\\n%s\\n\\n
64|The list is empty, but the file has NOT been touched. If you save or create a task, it will be rewritten: fix it first or restore the copy.
65|Tasks not loaded
66|TEST:
67|sent to %d window(s)
68|program started
69|Task “%s” fired.
"""

LANGS["pt"] = """
0|Agendador de tarefas · terminais e alarmes
1|Nome
2|Hora fixa
3|Aleatória no intervalo
4|Hora
5|De
6|até
7|(i) A hora exata é imprevisível dentro do intervalo → antirrastreamento.
8|Repetir todo dia
9|Digitar nos terminais
10|Executar programa / abrir
11|Filtro (título/processo)
12|Texto a enviar
13|Teclas antes
14|Janelas:
15|Todas
16|Primeira
17|Em foco
18|Pressionar Enter:
19|Corresponde ao TÍTULO ou ao PROCESSO (ex.: 'WindowsTerminal'); digita o texto + Enter.
20|Programa
21|Arquivo / URL
22|Argumentos
23|Pasta de trabalho
24|Modo da janela:
25|normal
26|minimizada
27|oculta
28|elevada
29|Som
30|Aviso pop-up
31|Mensagem do aviso
32|Salvar tarefa
33|Limpar
34|Testar agora
35|Parte do TÍTULO ou do nome do PROCESSO das janelas. Ex.: 'WindowsTerminal'.
36|O que é digitado em cada janela, seguido de Enter.
37|Teclas antes do texto. Ex.: esc  ou  ctrl+c  (separe várias com espaço).
38|Programa a executar. Args/Arquivo/URL são passados como argumentos.
39|Arquivo ou URL. Sem programa, abre com o app padrão.
40|Argumentos extras, no estilo da linha de comando (as aspas são respeitadas).
41|Pasta a partir da qual o programa é iniciado.
42|Tarefas agendadas
43|Editar
44|Ativar / pausar
45|Excluir
46|Atalhos:  Ctrl+S salvar · Ctrl+T testar · Esc limpar · Del excluir
47|Procurar…
48|Cancelar
49|Intervalo inválido
50|O intervalo 'de/até' não pode ser o mesmo minuto.
51|Tarefa salva.
52|Selecione primeiro uma tarefa da lista.
53|Tarefa '%s' excluída.
54|tarefa
55|Tarefa '%s' %s.
56|ATIVADA
57|PAUSADA
58|⏸  Pausar
59|▶  Ativar
60|Selecione uma tarefa da lista para editá-la.
61|Editando '%s': altere e toque em “Salvar tarefa”.
62|Não consegui ler alarms.json:\\n%s\\n\\n
63|Copiei-o para:\\n%s\\n\\n
64|A lista está vazia, mas o arquivo NÃO foi tocado. Se você salvar ou criar uma tarefa, ele será reescrito: corrija-o antes ou recupere a cópia.
65|Tarefas não carregadas
66|TESTE:
67|enviado a %d janela(s)
68|programa iniciado
69|Tarefa “%s” disparada.
"""

LANGS["fr"] = """
0|Planificateur de tâches · terminaux et alarmes
1|Nom
2|Heure fixe
3|Aléatoire dans un intervalle
4|Heure
5|De
6|à
7|(i) L’heure exacte est imprévisible dans l’intervalle → anti-traçage.
8|Répéter chaque jour
9|Écrire dans les terminaux
10|Lancer un programme / ouvrir
11|Filtre (titre/processus)
12|Texte à envoyer
13|Touches avant
14|Fenêtres :
15|Toutes
16|Première
17|Active
18|Appuyer sur Entrée :
19|Correspond au TITRE ou au PROCESSUS (ex. 'WindowsTerminal') ; tape le texte + Entrée.
20|Programme
21|Fichier / URL
22|Arguments
23|Dossier de travail
24|Mode fenêtre :
25|normal
26|réduit
27|caché
28|élevé
29|Son
30|Alerte
31|Message de l’alerte
32|Enregistrer la tâche
33|Effacer
34|Tester maintenant
35|Partie du TITRE ou du nom du PROCESSUS des fenêtres. Ex. : 'WindowsTerminal'.
36|Ce qui est tapé dans chaque fenêtre, suivi d’Entrée.
37|Touches avant le texte. Ex. : esc  ou  ctrl+c  (séparez-en plusieurs par des espaces).
38|Programme à lancer. Args/Fichier/URL lui sont passés en arguments.
39|Fichier ou URL. Sans programme, il s’ouvre avec l’application par défaut.
40|Arguments supplémentaires, façon ligne de commande (les guillemets sont respectés).
41|Dossier depuis lequel le programme est lancé.
42|Tâches planifiées
43|Modifier
44|Activer / suspendre
45|Supprimer
46|Raccourcis :  Ctrl+S enregistrer · Ctrl+T tester · Échap effacer · Suppr supprimer
47|Parcourir…
48|Annuler
49|Intervalle non valide
50|L’intervalle 'de/à' ne peut pas tenir dans la même minute.
51|Tâche enregistrée.
52|Sélectionnez d’abord une tâche dans la liste.
53|Tâche '%s' supprimée.
54|tâche
55|Tâche '%s' %s.
56|ACTIVÉE
57|SUSPENDUE
58|⏸  Suspendre
59|▶  Activer
60|Sélectionnez une tâche dans la liste pour la modifier.
61|Modification de '%s' : changez-la puis appuyez sur « Enregistrer la tâche ».
62|Impossible de lire alarms.json :\\n%s\\n\\n
63|Je l’ai copié dans :\\n%s\\n\\n
64|La liste est vide, mais le fichier n’a PAS été touché. Si vous enregistrez ou créez une tâche, il sera réécrit : corrigez-le d’abord ou récupérez la copie.
65|Tâches non chargées
66|TEST :
67|envoyé à %d fenêtre(s)
68|programme lancé
69|Tâche « %s » déclenchée.
"""

LANGS["de"] = """
0|Aufgabenplaner · Terminals und Wecker
1|Name
2|Feste Uhrzeit
3|Zufällig im Bereich
4|Uhrzeit
5|Von
6|bis
7|(i) Die genaue Uhrzeit ist innerhalb des Bereichs unvorhersehbar → Anti-Tracking.
8|Täglich wiederholen
9|In Terminals tippen
10|Programm starten / öffnen
11|Filter (Titel/Prozess)
12|Zu sendender Text
13|Tasten vorher
14|Fenster:
15|Alle
16|Erstes
17|Aktives
18|Enter drücken:
19|Passt auf TITEL oder PROZESS (z. B. 'WindowsTerminal'); tippt den Text + Enter.
20|Programm
21|Datei / URL
22|Argumente
23|Arbeitsordner
24|Fenstermodus:
25|normal
26|minimiert
27|versteckt
28|erhöht
29|Ton
30|Hinweisfenster
31|Hinweistext
32|Aufgabe speichern
33|Leeren
34|Jetzt testen
35|Teil des TITELS oder PROZESSNAMENS der Fenster. Z. B.: 'WindowsTerminal'.
36|Was in jedes Fenster getippt wird, gefolgt von Enter.
37|Tasten vor dem Text. Z. B.: esc  oder  ctrl+c  (mehrere mit Leerzeichen trennen).
38|Auszuführendes Programm. Args/Datei/URL werden ihm als Argumente übergeben.
39|Datei oder URL. Ohne Programm wird sie mit der Standard-App geöffnet.
40|Zusätzliche Argumente im Stil der Kommandozeile (Anführungszeichen werden beachtet).
41|Ordner, aus dem das Programm gestartet wird.
42|Geplante Aufgaben
43|Bearbeiten
44|Aktivieren / pausieren
45|Löschen
46|Tastenkürzel:  Strg+S speichern · Strg+T testen · Esc leeren · Entf löschen
47|Durchsuchen…
48|Abbrechen
49|Ungültiger Bereich
50|Der Bereich 'von/bis' darf nicht dieselbe Minute sein.
51|Aufgabe gespeichert.
52|Wähle zuerst eine Aufgabe in der Liste.
53|Aufgabe '%s' gelöscht.
54|Aufgabe
55|Aufgabe '%s' %s.
56|AKTIVIERT
57|PAUSIERT
58|⏸  Pausieren
59|▶  Aktivieren
60|Wähle eine Aufgabe in der Liste, um sie zu bearbeiten.
61|Bearbeite '%s': ändern und „Aufgabe speichern“ drücken.
62|alarms.json konnte nicht gelesen werden:\\n%s\\n\\n
63|Ich habe sie kopiert nach:\\n%s\\n\\n
64|Die Liste ist leer, aber die Datei wurde NICHT angerührt. Wenn du eine Aufgabe speicherst oder anlegst, wird sie überschrieben: repariere sie vorher oder stelle die Kopie wieder her.
65|Aufgaben nicht geladen
66|TEST:
67|an %d Fenster gesendet
68|Programm gestartet
69|Aufgabe „%s“ ausgelöst.
"""

LANGS["it"] = """
0|Pianificatore di attività · terminali e sveglie
1|Nome
2|Ora fissa
3|Casuale nell’intervallo
4|Ora
5|Da
6|a
7|(i) L’ora esatta è imprevedibile nell’intervallo → anti-tracciamento.
8|Ripeti ogni giorno
9|Scrivi nei terminali
10|Esegui programma / apri
11|Filtro (titolo/processo)
12|Testo da inviare
13|Tasti prima
14|Finestre:
15|Tutte
16|Prima
17|In primo piano
18|Premi Invio:
19|Corrisponde al TITOLO o al PROCESSO (es. 'WindowsTerminal'); digita il testo + Invio.
20|Programma
21|File / URL
22|Argomenti
23|Cartella di lavoro
24|Modalità finestra:
25|normale
26|ridotta
27|nascosta
28|elevata
29|Suono
30|Avviso
31|Messaggio dell’avviso
32|Salva attività
33|Pulisci
34|Prova ora
35|Parte del TITOLO o del nome del PROCESSO delle finestre. Es.: 'WindowsTerminal'.
36|Ciò che viene digitato in ogni finestra, seguito da Invio.
37|Tasti prima del testo. Es.: esc  o  ctrl+c  (separane più di uno con spazi).
38|Programma da eseguire. Args/File/URL gli vengono passati come argomenti.
39|File o URL. Senza programma, si apre con l’app predefinita.
40|Argomenti extra, stile riga di comando (le virgolette vengono rispettate).
41|Cartella da cui viene avviato il programma.
42|Attività pianificate
43|Modifica
44|Attiva / metti in pausa
45|Elimina
46|Scorciatoie:  Ctrl+S salva · Ctrl+T prova · Esc pulisci · Canc elimina
47|Sfoglia…
48|Annulla
49|Intervallo non valido
50|L’intervallo 'da/a' non può essere lo stesso minuto.
51|Attività salvata.
52|Seleziona prima un’attività dall’elenco.
53|Attività '%s' eliminata.
54|attività
55|Attività '%s' %s.
56|ATTIVATA
57|IN PAUSA
58|⏸  Pausa
59|▶  Attiva
60|Seleziona un’attività dall’elenco per modificarla.
61|Modifica di '%s': cambiala e premi “Salva attività”.
62|Non sono riuscito a leggere alarms.json:\\n%s\\n\\n
63|L’ho copiato in:\\n%s\\n\\n
64|L’elenco è vuoto, ma il file NON è stato toccato. Se salvi o crei un’attività verrà riscritto: sistemalo prima o recupera la copia.
65|Attività non caricate
66|PROVA:
67|inviato a %d finestra/e
68|programma avviato
69|Attività “%s” eseguita.
"""

LANGS["nl"] = """
0|Taakplanner · terminals en wekkers
1|Naam
2|Vaste tijd
3|Willekeurig in bereik
4|Tijd
5|Van
6|tot
7|(i) Het exacte tijdstip is onvoorspelbaar binnen het bereik → anti-tracking.
8|Elke dag herhalen
9|Typen in terminals
10|Programma starten / openen
11|Filter (titel/proces)
12|Te verzenden tekst
13|Toetsen vooraf
14|Vensters:
15|Alle
16|Eerste
17|Actieve
18|Enter drukken:
19|Komt overeen met TITEL of PROCES (bijv. 'WindowsTerminal'); typt de tekst + Enter.
20|Programma
21|Bestand / URL
22|Argumenten
23|Werkmap
24|Venstermodus:
25|normaal
26|geminimaliseerd
27|verborgen
28|verhoogd
29|Geluid
30|Pop-upmelding
31|Tekst van de melding
32|Taak opslaan
33|Wissen
34|Nu testen
35|Deel van de TITEL of de PROCESnaam van de vensters. Bijv.: 'WindowsTerminal'.
36|Wat er in elk venster wordt getypt, gevolgd door Enter.
37|Toetsen voor de tekst. Bijv.: esc  of  ctrl+c  (scheid meerdere met spaties).
38|Programma om te starten. Args/Bestand/URL worden als argumenten doorgegeven.
39|Bestand of URL. Zonder programma opent het met de standaardapp.
40|Extra argumenten, in opdrachtregelstijl (aanhalingstekens worden gerespecteerd).
41|Map van waaruit het programma wordt gestart.
42|Geplande taken
43|Bewerken
44|Activeren / pauzeren
45|Verwijderen
46|Sneltoetsen:  Ctrl+S opslaan · Ctrl+T testen · Esc wissen · Del verwijderen
47|Bladeren…
48|Annuleren
49|Ongeldig bereik
50|Het bereik 'van/tot' mag niet dezelfde minuut zijn.
51|Taak opgeslagen.
52|Selecteer eerst een taak in de lijst.
53|Taak '%s' verwijderd.
54|taak
55|Taak '%s' %s.
56|GEACTIVEERD
57|GEPAUZEERD
58|⏸  Pauzeren
59|▶  Activeren
60|Selecteer een taak in de lijst om die te bewerken.
61|'%s' bewerken: pas aan en druk op ‘Taak opslaan’.
62|Kon alarms.json niet lezen:\\n%s\\n\\n
63|Ik heb het gekopieerd naar:\\n%s\\n\\n
64|De lijst is leeg, maar het bestand is NIET aangeraakt. Als je een taak opslaat of maakt, wordt het overschreven: herstel het eerst of zet de kopie terug.
65|Taken niet geladen
66|TEST:
67|verzonden naar %d venster(s)
68|programma gestart
69|Taak ‘%s’ uitgevoerd.
"""

LANGS["pl"] = """
0|Harmonogram zadań · terminale i alarmy
1|Nazwa
2|Stała godzina
3|Losowo w przedziale
4|Godzina
5|Od
6|do
7|(i) Dokładna godzina jest nieprzewidywalna w przedziale → ochrona przed śledzeniem.
8|Powtarzaj codziennie
9|Pisz w terminalach
10|Uruchom program / otwórz
11|Filtr (tytuł/proces)
12|Tekst do wysłania
13|Klawisze przed
14|Okna:
15|Wszystkie
16|Pierwsze
17|Aktywne
18|Naciśnij Enter:
19|Pasuje do TYTUŁU lub PROCESU (np. 'WindowsTerminal'); wpisuje tekst + Enter.
20|Program
21|Plik / URL
22|Argumenty
23|Folder roboczy
24|Tryb okna:
25|normalny
26|zminimalizowany
27|ukryty
28|z uprawnieniami
29|Dźwięk
30|Powiadomienie
31|Treść powiadomienia
32|Zapisz zadanie
33|Wyczyść
34|Testuj teraz
35|Część TYTUŁU lub nazwy PROCESU okien. Np.: 'WindowsTerminal'.
36|To, co jest wpisywane w każdym oknie, a po tym Enter.
37|Klawisze przed tekstem. Np.: esc  lub  ctrl+c  (kilka oddziel spacjami).
38|Program do uruchomienia. Args/Plik/URL są przekazywane jako argumenty.
39|Plik lub URL. Bez programu otwiera się w domyślnej aplikacji.
40|Dodatkowe argumenty w stylu wiersza poleceń (cudzysłowy są respektowane).
41|Folder, z którego uruchamiany jest program.
42|Zaplanowane zadania
43|Edytuj
44|Włącz / wstrzymaj
45|Usuń
46|Skróty:  Ctrl+S zapisz · Ctrl+T testuj · Esc wyczyść · Del usuń
47|Przeglądaj…
48|Anuluj
49|Nieprawidłowy przedział
50|Przedział 'od/do' nie może mieścić się w tej samej minucie.
51|Zadanie zapisane.
52|Najpierw wybierz zadanie z listy.
53|Zadanie '%s' usunięte.
54|zadanie
55|Zadanie '%s' %s.
56|WŁĄCZONE
57|WSTRZYMANE
58|⏸  Wstrzymaj
59|▶  Włącz
60|Wybierz zadanie z listy, aby je edytować.
61|Edycja '%s': zmień i naciśnij „Zapisz zadanie”.
62|Nie mogłem odczytać alarms.json:\\n%s\\n\\n
63|Skopiowałem go do:\\n%s\\n\\n
64|Lista jest pusta, ale plik NIE został zmieniony. Jeśli zapiszesz lub utworzysz zadanie, zostanie nadpisany: najpierw go napraw albo przywróć kopię.
65|Zadania niewczytane
66|TEST:
67|wysłano do okien: %d
68|program uruchomiony
69|Zadanie „%s” uruchomione.
"""

LANGS["ru"] = """
0|Планировщик задач · терминалы и будильники
1|Название
2|Точное время
3|Случайно в интервале
4|Время
5|С
6|до
7|(i) Точное время непредсказуемо внутри интервала → защита от слежки.
8|Повторять каждый день
9|Печатать в терминалах
10|Запустить программу / открыть
11|Фильтр (заголовок/процесс)
12|Текст для отправки
13|Клавиши перед
14|Окна:
15|Все
16|Первое
17|Активное
18|Нажать Enter:
19|Совпадение по ЗАГОЛОВКУ или ПРОЦЕССУ (напр. 'WindowsTerminal'); печатает текст + Enter.
20|Программа
21|Файл / URL
22|Аргументы
23|Рабочая папка
24|Режим окна:
25|обычный
26|свёрнутый
27|скрытый
28|с правами админа
29|Звук
30|Всплывающее окно
31|Текст уведомления
32|Сохранить задачу
33|Очистить
34|Проверить сейчас
35|Часть ЗАГОЛОВКА или имени ПРОЦЕССА окон. Напр.: 'WindowsTerminal'.
36|Что печатается в каждом окне, затем Enter.
37|Клавиши перед текстом. Напр.: esc  или  ctrl+c  (несколько — через пробел).
38|Программа для запуска. Args/Файл/URL передаются ей как аргументы.
39|Файл или URL. Без программы открывается приложением по умолчанию.
40|Дополнительные аргументы в стиле командной строки (кавычки учитываются).
41|Папка, из которой запускается программа.
42|Запланированные задачи
43|Изменить
44|Включить / пауза
45|Удалить
46|Клавиши:  Ctrl+S сохранить · Ctrl+T проверить · Esc очистить · Del удалить
47|Обзор…
48|Отмена
49|Неверный интервал
50|Интервал 'с/до' не может быть одной и той же минутой.
51|Задача сохранена.
52|Сначала выберите задачу в списке.
53|Задача '%s' удалена.
54|задача
55|Задача '%s' %s.
56|ВКЛЮЧЕНА
57|НА ПАУЗЕ
58|⏸  Пауза
59|▶  Включить
60|Выберите задачу в списке, чтобы изменить её.
61|Изменение '%s': поправьте и нажмите «Сохранить задачу».
62|Не удалось прочитать alarms.json:\\n%s\\n\\n
63|Я скопировал его в:\\n%s\\n\\n
64|Список пуст, но файл НЕ тронут. Если сохраните или создадите задачу, он будет перезаписан: сначала исправьте его или восстановите копию.
65|Задачи не загружены
66|ТЕСТ:
67|отправлено в окон: %d
68|программа запущена
69|Задача «%s» сработала.
"""

LANGS["uk"] = """
0|Планувальник завдань · термінали й будильники
1|Назва
2|Точний час
3|Випадково в діапазоні
4|Час
5|З
6|до
7|(i) Точний час непередбачуваний у межах діапазону → захист від стеження.
8|Повторювати щодня
9|Друкувати в терміналах
10|Запустити програму / відкрити
11|Фільтр (заголовок/процес)
12|Текст для надсилання
13|Клавіші перед
14|Вікна:
15|Усі
16|Перше
17|Активне
18|Натиснути Enter:
19|Збіг за ЗАГОЛОВКОМ або ПРОЦЕСОМ (напр. 'WindowsTerminal'); друкує текст + Enter.
20|Програма
21|Файл / URL
22|Аргументи
23|Робоча тека
24|Режим вікна:
25|звичайний
26|згорнутий
27|прихований
28|з правами адміна
29|Звук
30|Спливне вікно
31|Текст сповіщення
32|Зберегти завдання
33|Очистити
34|Перевірити зараз
35|Частина ЗАГОЛОВКА або назви ПРОЦЕСУ вікон. Напр.: 'WindowsTerminal'.
36|Що друкується в кожному вікні, а потім Enter.
37|Клавіші перед текстом. Напр.: esc  або  ctrl+c  (кілька — через пробіл).
38|Програма для запуску. Args/Файл/URL передаються їй як аргументи.
39|Файл або URL. Без програми відкривається типовим застосунком.
40|Додаткові аргументи у стилі командного рядка (лапки враховуються).
41|Тека, з якої запускається програма.
42|Заплановані завдання
43|Змінити
44|Увімкнути / пауза
45|Видалити
46|Клавіші:  Ctrl+S зберегти · Ctrl+T перевірити · Esc очистити · Del видалити
47|Огляд…
48|Скасувати
49|Неправильний діапазон
50|Діапазон 'з/до' не може бути однією й тією ж хвилиною.
51|Завдання збережено.
52|Спершу виберіть завдання у списку.
53|Завдання '%s' видалено.
54|завдання
55|Завдання '%s' %s.
56|УВІМКНЕНО
57|НА ПАУЗІ
58|⏸  Пауза
59|▶  Увімкнути
60|Виберіть завдання у списку, щоб змінити його.
61|Зміна '%s': виправте й натисніть «Зберегти завдання».
62|Не вдалося прочитати alarms.json:\\n%s\\n\\n
63|Я скопіював його до:\\n%s\\n\\n
64|Список порожній, але файл НЕ змінено. Якщо збережете або створите завдання, його буде перезаписано: спершу виправте його або відновіть копію.
65|Завдання не завантажено
66|ТЕСТ:
67|надіслано у вікон: %d
68|програму запущено
69|Завдання «%s» спрацювало.
"""

LANGS["zh"] = """
0|任务计划 · 终端与闹钟
1|名称
2|固定时间
3|范围内随机
4|时间
5|从
6|到
7|(i) 精确时间在范围内无法预测 → 防追踪。
8|每天重复
9|在终端中输入
10|运行程序 / 打开
11|筛选（标题/进程）
12|要发送的文字
13|先按的键
14|窗口：
15|全部
16|第一个
17|当前窗口
18|按 Enter：
19|按标题或进程匹配（例如 'WindowsTerminal'），输入文字后按 Enter。
20|程序
21|文件 / URL
22|参数
23|工作目录
24|窗口模式：
25|正常
26|最小化
27|隐藏
28|管理员
29|声音
30|弹出提醒
31|提醒内容
32|保存任务
33|清空
34|立即测试
35|窗口标题或进程名的一部分。例如：'WindowsTerminal'。
36|在每个窗口中输入的内容，随后按 Enter。
37|文字前要按的键。例如：esc 或 ctrl+c（多个用空格分隔）。
38|要运行的程序。参数/文件/URL 会作为参数传给它。
39|文件或 URL。不指定程序时用默认应用打开。
40|额外参数，按命令行格式（保留引号）。
41|启动程序时所在的文件夹。
42|计划任务
43|编辑
44|启用 / 暂停
45|删除
46|快捷键：Ctrl+S 保存 · Ctrl+T 测试 · Esc 清空 · Del 删除
47|浏览…
48|取消
49|范围无效
50|“从/到”范围不能在同一分钟。
51|任务已保存。
52|请先在列表中选择一个任务。
53|任务“%s”已删除。
54|任务
55|任务“%s”%s。
56|已启用
57|已暂停
58|⏸  暂停
59|▶  启用
60|请在列表中选择要编辑的任务。
61|正在编辑“%s”：修改后点击“保存任务”。
62|无法读取 alarms.json：\\n%s\\n\\n
63|已复制到：\\n%s\\n\\n
64|列表为空，但文件没有被改动。如果保存或新建任务，它会被覆盖：请先修复，或恢复副本。
65|任务未加载
66|测试：
67|已发送到 %d 个窗口
68|程序已启动
69|任务“%s”已触发。
"""

LANGS["ja"] = """
0|タスクスケジューラー · ターミナルとアラーム
1|名前
2|固定時刻
3|範囲内でランダム
4|時刻
5|開始
6|〜
7|(i) 範囲内の正確な時刻は予測できません → 追跡防止。
8|毎日繰り返す
9|ターミナルに入力
10|プログラムを実行 / 開く
11|フィルター（タイトル/プロセス）
12|送信するテキスト
13|先に押すキー
14|ウィンドウ：
15|すべて
16|最初
17|アクティブ
18|Enter を押す回数：
19|タイトルかプロセスで一致（例 'WindowsTerminal'）。テキスト + Enter を入力します。
20|プログラム
21|ファイル / URL
22|引数
23|作業フォルダー
24|ウィンドウ：
25|通常
26|最小化
27|非表示
28|管理者
29|サウンド
30|ポップアップ
31|ポップアップのメッセージ
32|タスクを保存
33|クリア
34|今すぐテスト
35|ウィンドウのタイトルかプロセス名の一部。例：'WindowsTerminal'。
36|各ウィンドウに入力する内容（最後に Enter）。
37|テキストの前に押すキー。例：esc または ctrl+c（複数はスペース区切り）。
38|実行するプログラム。引数/ファイル/URL は引数として渡されます。
39|ファイルまたは URL。プログラムがなければ既定のアプリで開きます。
40|追加の引数（コマンドライン形式、引用符も有効）。
41|プログラムを起動するフォルダー。
42|予定されたタスク
43|編集
44|有効 / 一時停止
45|削除
46|ショートカット：Ctrl+S 保存 · Ctrl+T テスト · Esc クリア · Del 削除
47|参照…
48|キャンセル
49|範囲が無効です
50|「開始/〜」の範囲を同じ分にはできません。
51|タスクを保存しました。
52|先に一覧からタスクを選んでください。
53|タスク「%s」を削除しました。
54|タスク
55|タスク「%s」は%s。
56|有効になりました
57|一時停止しました
58|⏸  一時停止
59|▶  有効にする
60|編集するタスクを一覧から選んでください。
61|「%s」を編集中：変更して「タスクを保存」を押してください。
62|alarms.json を読めませんでした：\\n%s\\n\\n
63|コピーした場所：\\n%s\\n\\n
64|一覧は空ですが、ファイルには手を付けていません。タスクを保存・作成すると上書きされます。先に直すか、コピーから戻してください。
65|タスクを読み込めませんでした
66|テスト：
67|%d 個のウィンドウに送信
68|プログラムを起動しました
69|タスク「%s」を実行しました。
"""

LANGS["ko"] = """
0|작업 예약 · 터미널과 알람
1|이름
2|고정 시각
3|범위 내 무작위
4|시각
5|시작
6|~
7|(i) 범위 안의 정확한 시각은 예측할 수 없습니다 → 추적 방지.
8|매일 반복
9|터미널에 입력
10|프로그램 실행 / 열기
11|필터(제목/프로세스)
12|보낼 텍스트
13|먼저 누를 키
14|창:
15|모두
16|첫 번째
17|활성 창
18|Enter 횟수:
19|제목이나 프로세스로 찾습니다(예: 'WindowsTerminal'). 텍스트 + Enter를 입력합니다.
20|프로그램
21|파일 / URL
22|인수
23|작업 폴더
24|창 모드:
25|일반
26|최소화
27|숨김
28|관리자
29|소리
30|팝업 알림
31|알림 메시지
32|작업 저장
33|지우기
34|지금 테스트
35|창 제목이나 프로세스 이름의 일부. 예: 'WindowsTerminal'.
36|각 창에 입력할 내용(끝에 Enter).
37|텍스트 앞에 누를 키. 예: esc 또는 ctrl+c(여러 개는 공백으로 구분).
38|실행할 프로그램. 인수/파일/URL이 인수로 전달됩니다.
39|파일이나 URL. 프로그램이 없으면 기본 앱으로 엽니다.
40|추가 인수, 명령줄 형식(따옴표 유지).
41|프로그램을 시작할 폴더.
42|예약된 작업
43|편집
44|켜기 / 일시 중지
45|삭제
46|단축키:  Ctrl+S 저장 · Ctrl+T 테스트 · Esc 지우기 · Del 삭제
47|찾아보기…
48|취소
49|잘못된 범위
50|‘시작/~’ 범위가 같은 분일 수 없습니다.
51|작업을 저장했습니다.
52|먼저 목록에서 작업을 고르세요.
53|‘%s’ 작업을 삭제했습니다.
54|작업
55|‘%s’ 작업: %s.
56|켜짐
57|일시 중지됨
58|⏸  일시 중지
59|▶  켜기
60|편집할 작업을 목록에서 고르세요.
61|‘%s’ 편집 중: 바꾼 뒤 ‘작업 저장’을 누르세요.
62|alarms.json을 읽지 못했습니다:\\n%s\\n\\n
63|복사한 위치:\\n%s\\n\\n
64|목록은 비어 있지만 파일은 건드리지 않았습니다. 작업을 저장하거나 만들면 덮어씁니다. 먼저 고치거나 사본을 복원하세요.
65|작업을 불러오지 못함
66|테스트:
67|창 %d개에 보냄
68|프로그램을 실행함
69|‘%s’ 작업이 실행되었습니다.
"""

LANGS["th"] = """
0|ตัวตั้งเวลางาน · เทอร์มินัลและนาฬิกาปลุก
1|ชื่อ
2|เวลาที่แน่นอน
3|สุ่มในช่วง
4|เวลา
5|ตั้งแต่
6|ถึง
7|(i) เวลาที่แน่นอนคาดเดาไม่ได้ภายในช่วง → ป้องกันการติดตาม
8|ทำซ้ำทุกวัน
9|พิมพ์ในเทอร์มินัล
10|เรียกใช้โปรแกรม / เปิด
11|ตัวกรอง (ชื่อหน้าต่าง/โปรเซส)
12|ข้อความที่จะส่ง
13|ปุ่มที่กดก่อน
14|หน้าต่าง:
15|ทั้งหมด
16|แรก
17|ที่โฟกัส
18|กด Enter:
19|ตรงกับชื่อหน้าต่างหรือโปรเซส (เช่น 'WindowsTerminal') แล้วพิมพ์ข้อความ + Enter
20|โปรแกรม
21|ไฟล์ / URL
22|อาร์กิวเมนต์
23|โฟลเดอร์ทำงาน
24|โหมดหน้าต่าง:
25|ปกติ
26|ย่อ
27|ซ่อน
28|ผู้ดูแลระบบ
29|เสียง
30|ป๊อปอัป
31|ข้อความป๊อปอัป
32|บันทึกงาน
33|ล้าง
34|ทดสอบตอนนี้
35|ส่วนหนึ่งของชื่อหน้าต่างหรือชื่อโปรเซส เช่น 'WindowsTerminal'
36|ข้อความที่พิมพ์ในแต่ละหน้าต่าง ตามด้วย Enter
37|ปุ่มที่กดก่อนข้อความ เช่น esc หรือ ctrl+c (หลายปุ่มคั่นด้วยเว้นวรรค)
38|โปรแกรมที่จะเรียกใช้ อาร์กิวเมนต์/ไฟล์/URL จะส่งให้เป็นอาร์กิวเมนต์
39|ไฟล์หรือ URL ถ้าไม่มีโปรแกรม จะเปิดด้วยแอปเริ่มต้น
40|อาร์กิวเมนต์เพิ่มเติม แบบบรรทัดคำสั่ง (คงเครื่องหมายคำพูด)
41|โฟลเดอร์ที่ใช้เริ่มโปรแกรม
42|งานที่ตั้งเวลาไว้
43|แก้ไข
44|เปิด / หยุดชั่วคราว
45|ลบ
46|ทางลัด:  Ctrl+S บันทึก · Ctrl+T ทดสอบ · Esc ล้าง · Del ลบ
47|เลือก…
48|ยกเลิก
49|ช่วงไม่ถูกต้อง
50|ช่วง 'ตั้งแต่/ถึง' ต้องไม่ใช่นาทีเดียวกัน
51|บันทึกงานแล้ว
52|เลือกงานในรายการก่อน
53|ลบงาน '%s' แล้ว
54|งาน
55|งาน '%s' %s
56|เปิดแล้ว
57|หยุดชั่วคราวแล้ว
58|⏸  หยุดชั่วคราว
59|▶  เปิด
60|เลือกงานในรายการเพื่อแก้ไข
61|กำลังแก้ไข '%s': แก้แล้วกด “บันทึกงาน”
62|อ่าน alarms.json ไม่ได้:\\n%s\\n\\n
63|คัดลอกไว้ที่:\\n%s\\n\\n
64|รายการว่างเปล่า แต่ไม่ได้แตะต้องไฟล์ หากบันทึกหรือสร้างงาน ไฟล์จะถูกเขียนทับ: แก้ไขก่อนหรือกู้คืนจากสำเนา
65|โหลดงานไม่ได้
66|ทดสอบ:
67|ส่งไปยัง %d หน้าต่าง
68|เรียกใช้โปรแกรมแล้ว
69|งาน “%s” ทำงานแล้ว
"""

LANGS["hi"] = """
0|टास्क शेड्यूलर · टर्मिनल और अलार्म
1|नाम
2|तय समय
3|दायरे में रैंडम
4|समय
5|से
6|तक
7|(i) दायरे के भीतर सही समय का अंदाज़ा नहीं लगाया जा सकता → ट्रैकिंग से बचाव।
8|हर दिन दोहराएँ
9|टर्मिनल में लिखें
10|प्रोग्राम चलाएँ / खोलें
11|फ़िल्टर (शीर्षक/प्रोसेस)
12|भेजने वाला टेक्स्ट
13|पहले दबाने वाली कुंजियाँ
14|विंडो:
15|सभी
16|पहली
17|सक्रिय
18|Enter दबाएँ:
19|शीर्षक या प्रोसेस से मिलान (जैसे 'WindowsTerminal'); टेक्स्ट + Enter लिखता है।
20|प्रोग्राम
21|फ़ाइल / URL
22|आर्ग्युमेंट
23|कार्य फ़ोल्डर
24|विंडो मोड:
25|सामान्य
26|छोटा किया
27|छिपा
28|एडमिन
29|आवाज़
30|पॉप-अप सूचना
31|सूचना का संदेश
32|टास्क सेव करें
33|साफ़ करें
34|अभी आज़माएँ
35|विंडो के शीर्षक या प्रोसेस के नाम का हिस्सा। जैसे: 'WindowsTerminal'।
36|हर विंडो में जो लिखा जाता है, उसके बाद Enter।
37|टेक्स्ट से पहले की कुंजियाँ। जैसे: esc या ctrl+c (कई हों तो स्पेस से अलग करें)।
38|चलाने वाला प्रोग्राम। Args/फ़ाइल/URL उसे आर्ग्युमेंट के रूप में दिए जाते हैं।
39|फ़ाइल या URL। प्रोग्राम न हो तो डिफ़ॉल्ट ऐप से खुलता है।
40|अतिरिक्त आर्ग्युमेंट, कमांड-लाइन की तरह (उद्धरण चिह्न माने जाते हैं)।
41|वह फ़ोल्डर जहाँ से प्रोग्राम शुरू होता है।
42|शेड्यूल किए गए टास्क
43|बदलें
44|चालू / रोकें
45|मिटाएँ
46|शॉर्टकट:  Ctrl+S सेव · Ctrl+T आज़माएँ · Esc साफ़ · Del मिटाएँ
47|ब्राउज़ करें…
48|रद्द करें
49|अमान्य दायरा
50|'से/तक' का दायरा एक ही मिनट नहीं हो सकता।
51|टास्क सेव हो गया।
52|पहले सूची से कोई टास्क चुनें।
53|टास्क '%s' मिटा दिया गया।
54|टास्क
55|टास्क '%s' %s।
56|चालू
57|रुका हुआ
58|⏸  रोकें
59|▶  चालू करें
60|बदलने के लिए सूची से कोई टास्क चुनें।
61|'%s' बदला जा रहा है: बदलाव करें और “टास्क सेव करें” दबाएँ।
62|alarms.json पढ़ा नहीं जा सका:\\n%s\\n\\n
63|इसे यहाँ कॉपी किया:\\n%s\\n\\n
64|सूची खाली है, पर फ़ाइल को छुआ नहीं गया। टास्क सेव करने या बनाने पर वह फिर से लिखी जाएगी: पहले उसे ठीक करें या कॉपी वापस लाएँ।
65|टास्क लोड नहीं हुए
66|टेस्ट:
67|%d विंडो में भेजा गया
68|प्रोग्राम शुरू हुआ
69|टास्क “%s” चल गया।
"""

SUPPORTED = ["es"] + list(LANGS)


def _parse():
    tables = {}
    for lang, block in LANGS.items():
        t = {}
        for line in block.split("\n"):
            if line.strip():
                n, text = line.split("|", 1)
                t[int(n)] = text.replace("\\n", "\n")
        assert sorted(t) == list(range(len(SOURCE))), (lang, sorted(set(range(len(SOURCE))) - set(t)))
        for i, src in enumerate(SOURCE):
            assert re.findall(r"%[sd]", src) == re.findall(r"%[sd]", t[i]), (lang, i)
        tables[lang] = {SOURCE[i]: t[i] for i in t}
    return tables


TABLES = _parse()


def _system_lang():
    try:
        if sys.platform == "win32":
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return locale.windows_locale.get(lcid, "")
        return os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    except Exception:
        return ""


def pick_lang(argv=None):
    argv = sys.argv if argv is None else argv
    wanted = ""
    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv):
            wanted = argv[i + 1]
    wanted = wanted or os.environ.get("TTA_LANG", "") or _system_lang()
    base = wanted.lower().replace("-", "_").split("_")[0].split(".")[0]
    return base if base in SUPPORTED else "en"


LANG = pick_lang()


def _(text):
    """The Spanish original in the chosen language (itself in Spanish, or if unknown)."""
    if LANG == "es":
        return text
    return TABLES[LANG].get(text, text)
