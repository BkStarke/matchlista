import os
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime, timedelta


class ExcelSheetSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel Bladsväljare")

        # Hämta aktuell mapp
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # Skapa GUI-element
        self.create_widgets()

    def create_widgets(self):
        # Filväljare
        tk.Label(self.root, text="Välj Excel-fil:").pack(pady=5)
        self.file_path = tk.StringVar()
        tk.Entry(self.root, textvariable=self.file_path, width=50).pack(pady=5)
        tk.Button(self.root, text="Bläddra...", command=self.browse_file).pack(pady=5)

        # Bladsväljare
        tk.Label(self.root, text="Välj blad:").pack(pady=5)
        self.sheet_var = tk.StringVar()
        self.sheet_dropdown = tk.OptionMenu(self.root, self.sheet_var, "")
        self.sheet_dropdown.pack(pady=5)
        self.sheet_dropdown.config(state="disabled")

        # Bekräfta knapp
        tk.Button(self.root, text="Ändra HTML", command=lambda: run_button(self.file_path.get(), self.sheet_var.get())).pack(pady=20)

    def browse_file(self):
        # Visa dialogruta för att välja Excel-fil
        file_path = filedialog.askopenfilename(
            initialdir=self.current_dir,
            title="Välj Excel-fil",
            filetypes=(("Excel-filer", "*.xlsx *.xls"), ("Alla filer", "*.*"))
        )

        if file_path:
            self.file_path.set(file_path)
            self.load_sheets(file_path)

    def load_sheets(self, file_path):
        try:
            # Läs alla blad från Excel-filen med explicit teckenkodning
            xls = pd.ExcelFile(file_path, engine='openpyxl')
            sheets = xls.sheet_names

            # Uppdatera dropdown-menyn
            self.sheet_dropdown['menu'].delete(0, 'end')
            for sheet in sheets:
                self.sheet_dropdown['menu'].add_command(
                    label=sheet,
                    command=tk._setit(self.sheet_var, sheet)
                )

            self.sheet_dropdown.config(state="normal")
            if sheets:
                self.sheet_var.set(sheets[0])

        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte läsa Excel-filen:\n{str(e)}")

    def confirm_selection(self):
        file = self.file_path.get()
        sheet = self.sheet_var.get()

        if not file:
            messagebox.showwarning("Varning", "Välj en Excel-fil först!")
            return

        if not sheet:
            messagebox.showwarning("Varning", "Inget blad valt!")
            return

        messagebox.showinfo("Val", f"Du har valt:\nFil: {file}\nBlad: {sheet}")

def excel_to_text_string(input_file, sheet_name=None):
    """
    Konverterar ett Excel-ark till en textsträng (tab-separerad, nyrads-separerad).
    Bevara specialtecken som å, ä, ö.

    Args:
        input_file (str): Sökväg till Excel-filen
        sheet_name (str, optional): Namn på arket att konvertera. Default är första arket.

    Returns:
        str: Den konverterade textsträngen (tab-separerad, nyrads-separerad)

    Raises:
        FileNotFoundError: Om filen inte hittas
        ValueError: Om angivet ark inte finns
        Exception: Vid andra fel
    """
    # Läs Excel-filen med openpyxl motor för bättre teckenhantering
    xls = pd.ExcelFile(input_file, engine='openpyxl')

    # Kontrollera om angivet ark finns
    if sheet_name is not None and sheet_name not in xls.sheet_names:
        available_sheets = ", ".join(xls.sheet_names)
        raise ValueError(f"Arket '{sheet_name}' finns inte. Tillgängliga ark: {available_sheets}")

    # Använd första arket om inget anges
    sheet_to_use = sheet_name if sheet_name else xls.sheet_names[0]

    # Läs arket (utan header) och bevara specialtecken
    df = pd.read_excel(xls, sheet_name=sheet_to_use, header=None, dtype=str)

    # Konvertera till textsträng (tab-separerad) och returnera med UTF-8 kodning
    return df.to_csv(sep='\t', index=False, header=False, encoding='utf-8')

def parse_schedule(input_text):
    schedule_data = {}
    mat_end_times = defaultdict(dict)  # För att spara sluttider per matta

    lines = [line.strip() for line in input_text.split('\n') if line.strip()]

    if not lines:
        return {}

    # Extrahera rubrikraden för att bestämma antal mattor
    headers = [h.strip() for h in lines[0].split('\t') if h.strip()]
    num_mats = len(headers) - 2  # Dra bort Match # och Tid kolumnerna

    for line in lines[1:]:
        if not line.strip():
            continue

        columns = [col.strip() for col in line.split('\t') if col.strip()]

        if len(columns) < 3:  # Behöver minst Match #, Tid och en matta
            continue

        match_num = columns[0]
        time_str = columns[1]

        # Hantera tider med sekunder (HH:MM:SS)
        try:
            if time_str.count(':') == 2:
                hours, minutes, seconds = map(int, time_str.split(':'))
                if not (0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60):
                    continue
                time_display = f"{hours:02d}:{minutes:02d}"  # Visa utan sekunder
            else:
                # Fallback för HH:MM format
                hours, minutes = map(int, time_str.split(':'))
                time_display = time_str
        except ValueError:
            continue

        # Bestäm faktiskt antal mattor i denna rad
        actual_mats = min(num_mats, len(columns) - 2)

        for mat_idx in range(actual_mats):
            mat_name = f"Matta {mat_idx + 1}"
            match_str = columns[mat_idx + 2]

            if not match_str or 'vs' not in match_str:
                continue

            try:
                participants = [p.strip() for p in match_str.split('vs')]
                if len(participants) != 2:
                    continue

                # Hämta tidigare sluttid för denna matta
                prev_end_time = mat_end_times[mat_name].get('end_time')

                if prev_end_time:
                    # Använd föregående sluttid som starttid
                    start_time = prev_end_time
                else:
                    # Första matchen på denna matta, använd angiven tid
                    start_time = time_display

                # Beräkna sluttid (5 minuters matchtid)
                start_h, start_m = map(int, start_time.split(':'))
                end_m = start_m + 5
                end_h = start_h
                if end_m >= 60:
                    end_h += 1
                    end_m -= 60
                end_time = f"{end_h:02d}:{end_m:02d}"

                # Spara sluttiden för nästa match
                mat_end_times[mat_name]['end_time'] = end_time

                time_range = f"{start_time}-{end_time}"

                # Processa båda deltagarna
                participant1, participant2 = participants
                for participant, opponent in [(participant1, participant2), (participant2, participant1)]:
                    # Extrahera namn (hantera fall med/utan klubb)
                    name = participant.split('(')[0].strip()
                    if not name:
                        continue

                    if name not in schedule_data:
                        schedule_data[name] = []

                    schedule_data[name].append({
                        'match': match_num,
                        'time': time_range,
                        'opponent': opponent,
                        'mat': mat_name
                    })

            except (ValueError, IndexError) as e:
                print(f"Fel vid bearbetning av rad: {line}. Fel: {e}")
                continue

    output_json = json.dumps(schedule_data, indent=4, ensure_ascii=False)

    return output_json

def convert_to_html_table(input_text):
    lines = [line.strip() for line in input_text.split('\n') if line.strip()]

    # Extract headers (first line)
    headers = lines[0].split('\t')

    # Extract all matches data
    matches = []
    for line in lines[1:]:
        cols = line.split('\t')
        matches.append({
            'match_num': cols[0],
            'time': cols[1],
            'mattor': cols[2:]
        })

    # Function to parse time with flexible format
    def parse_time(time_str):
        try:
            return datetime.strptime(time_str, "%H:%M")
        except ValueError:
            try:
                return datetime.strptime(time_str, "%H:%M:%S")
            except ValueError:
                # Fallback if time format is unexpected
                parts = time_str.split(':')
                if len(parts) >= 2:
                    return datetime.strptime(f"{parts[0]}:{parts[1]}", "%H:%M")
                raise

    # Calculate match durations and end times
    if len(matches) > 1:
        durations = []
        for i in range(len(matches) - 1):
            time1 = parse_time(matches[i]['time'])
            time2 = parse_time(matches[i + 1]['time'])
            duration = (time2 - time1).seconds // 60  # duration in minutes
            durations.append(duration)
            matches[i]['end_time'] = matches[i + 1]['time']

        avg_duration = sum(durations) // len(durations) if durations else 4
    else:
        avg_duration = 4  # default if only one match

    # Calculate end time for all matches (including last)
    for i in range(len(matches)):
        if i < len(matches) - 1:
            matches[i]['end_time'] = matches[i + 1]['time']
        else:
            # For last match, calculate end time based on average duration
            start_time = parse_time(matches[i]['time'])
            end_time = (start_time + timedelta(minutes=avg_duration)).strftime("%H:%M")
            matches[i]['end_time'] = end_time

    html_output = ['<table>']

    # Add table headers
    html_output.append('            <tr>')
    for header in headers:
        html_output.append(f'                <th>{header}</th>')
    html_output.append('            </tr>')

    # Process each match
    for match in matches:
        # Add comment with round number
        html_output.append(f'            <!-- Round {match["match_num"]} ({match["time"]}-{match["end_time"]}) -->')

        # Start table row
        html_output.append('            <tr>')

        # Add Match # column
        html_output.append(f'                <td>{match["match_num"]}</td>')

        # Format time (remove seconds if present)
        start_time = ':'.join(match['time'].split(':')[:2])
        end_time = ':'.join(match['end_time'].split(':')[:2])

        # Add time column with interval
        html_output.append(f'                <td>{start_time}-{end_time}</td>')

        # Process each matta column
        for matta in match['mattor']:
            if ' vs ' in matta:
                participants = matta.split(' vs ')
                formatted_participants = []
                for participant in participants:
                    if '(' in participant:
                        name, club = participant.split('(')
                        club = club.rstrip(')')
                        formatted = f'<a href="#" onclick="showSchedule(\'{name.strip()}\')">{name.strip()}</a> ({club})'
                    else:
                        formatted = f'<a href="#" onclick="showSchedule(\'{participant.strip()}\')">{participant.strip()}</a>'
                    formatted_participants.append(formatted)
                cell_content = ' vs '.join(formatted_participants)
            else:
                cell_content = matta

            html_output.append(f'                <td>{cell_content}</td>')

        # Close table row
        html_output.append('            </tr>')

    # Close table
    html_output.append('</table>')

    return '\n'.join(html_output)

def process_table_data(table_data):
    # Dela upp tabellen i rader
    lines = table_data.strip().split('\n')

    # Extrahera rubrikraden
    headers = lines[0].split('\t')

    # Hitta kolumnindex för "Tid"
    try:
        time_col_index = headers.index("Tid")
    except ValueError:
        return "Kolumnen 'Tid' hittades inte i tabellen."

    # Extrahera alla tider
    times = []
    for line in lines[1:]:  # Hoppa över rubrikraden
        columns = line.split('\t')
        if len(columns) > time_col_index:
            time_str = columns[time_col_index].strip()
            if time_str:  # Kontrollera att det inte är tomt
                times.append(time_str)

    if not times:
        return "Inga tider hittades i tabellen."

    # Konvertera tiderna till datetime-objekt
    time_objects = []
    for time_str in times:
        try:
            # Hantera både "HH:MM" och "HH:MM:SS" format
            if time_str.count(':') == 1:
                time_obj = datetime.strptime(time_str, "%H:%M")
            else:
                time_obj = datetime.strptime(time_str, "%H:%M:%S")
            time_objects.append(time_obj)
        except ValueError as e:
            print(f"Kunde inte tolka tid: {time_str} - {e}")
            continue

    if not time_objects:
        return "Inga giltiga tider kunde tolkas."

    # Sortera tiderna
    time_objects.sort()

    # Beräkna första och sista tid
    first_time = time_objects[0]
    last_time = time_objects[-1]

    # Beräkna intervallet (om det finns fler än en tid)
    if len(time_objects) > 1:
        interval = time_objects[1] - time_objects[0]
        last_time += interval

    # Formatera utdata
    time_range = f"<h2>{first_time.strftime('%H:%M')}-{last_time.strftime('%H:%M')}</h2>"
    return time_range

def run_button(excel, blad):
    tabell = excel_to_text_string(excel, blad)

    # Skriv filerna med UTF-8 kodning för att bevara specialtecken
    with open('tabell.html', 'w', encoding='utf-8') as file:
        file.write(convert_to_html_table(tabell))

    with open('json.json', 'w', encoding='utf-8') as file:
        file.write(parse_schedule(tabell))

    with open('tid.html', 'w', encoding='utf-8') as file:
        file.write(process_table_data(tabell))

if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelSheetSelector(root)
    root.mainloop()