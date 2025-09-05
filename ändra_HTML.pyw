import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime, timedelta

# --- Hjälpfunktion för flexibel tidstolkning ---
def parse_time_str(time_str):
    """
    Tolkar tid från sträng. Stöder "HH:MM", "HH:MM:SS" och varianter med ".000".
    Returnerar en datetime (samme dag, datum irrelevant).
    Kastar ValueError om tiden inte kan tolkas.
    """
    if time_str is None:
        raise ValueError("Tom tid")
    s = str(time_str).strip()
    # Ta bort eventuella citattecken
    s = s.strip('"').strip("'")
    # Försök standardformat
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    # Hantera "HH:MM:SS.ffffff" eller "HH:MM:SS.000"
    if '.' in s:
        part = s.split('.', 1)[0]
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(part, fmt)
            except ValueError:
                pass
    # Rensa bort icke-siffror utom ":" och prova igen
    cleaned = re.sub(r'[^0-9:]', '', s)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            pass
    raise ValueError(f"Kan inte tolka tiden: '{time_str}'")


def calculate_match_length(input_text):
    """
    Räkna ut matchlängd (i minuter) baserat på starttider i input_text.
    Tar skillnaden mellan första och andra matchens starttid.
    Fallback = 4 minuter om det inte går att räkna ut.
    """
    lines = [line for line in input_text.split('\n') if line.strip()]
    times = []
    for line in lines[1:]:
        cols = line.split('\t')
        if len(cols) < 2:
            continue
        try:
            t = parse_time_str(cols[1].strip())
            times.append(t)
        except Exception:
            continue
    if len(times) < 2:
        return 4
    diff_min = (times[1] - times[0]).seconds // 60
    return max(1, diff_min)


class ExcelSheetSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel Bladsväljare")
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.selected_file = None
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="Välj Excel-fil:").pack(pady=5)
        self.file_path = tk.StringVar()
        tk.Entry(self.root, textvariable=self.file_path, width=50).pack(pady=5)
        tk.Button(self.root, text="Bläddra...", command=self.browse_file).pack(pady=5)

        tk.Label(self.root, text="Välj blad:").pack(pady=5)
        self.sheet_var = tk.StringVar()
        self.sheet_dropdown = tk.OptionMenu(self.root, self.sheet_var, "")
        self.sheet_dropdown.pack(pady=5)
        self.sheet_dropdown.config(state="disabled")

        tk.Label(self.root, text="Välj vilotid (minuter):").pack(pady=5)
        self.rest_time_var = tk.IntVar(value=0)
        # Skapa Spinbox men uppdatera "to" senare baserat på matchlängd
        self.rest_time_spinbox = tk.Spinbox(self.root, from_=0, to=10, textvariable=self.rest_time_var, width=5)
        self.rest_time_spinbox.pack(pady=5)

        tk.Button(self.root, text="Ändra HTML", command=self.generate_outputs).pack(pady=20)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.current_dir,
            title="Välj Excel-fil",
            filetypes=(("Excel-filer", "*.xlsx *.xls"), ("Alla filer", "*.*"))
        )
        if file_path:
            self.selected_file = file_path
            self.file_path.set(file_path)
            self.load_sheets(file_path)

    def load_sheets(self, file_path):
        try:
            xls = pd.ExcelFile(file_path, engine='openpyxl')
            sheets = xls.sheet_names
            menu = self.sheet_dropdown['menu']
            menu.delete(0, 'end')
            for sheet in sheets:
                # använd lambda för att både sätta variabeln och köra on_sheet_selected
                menu.add_command(label=sheet, command=lambda s=sheet: self.on_sheet_selected(s))
            self.sheet_dropdown.config(state="normal")
            if sheets:
                # välj första bladet och uppdatera vilotidsgräns
                self.sheet_var.set(sheets[0])
                self.update_rest_limit(file_path, sheets[0])
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte läsa Excel-filen:\n{str(e)}")

    def on_sheet_selected(self, sheet):
        # Används från menyn
        self.sheet_var.set(sheet)
        if self.selected_file:
            self.update_rest_limit(self.selected_file, sheet)

    def update_rest_limit(self, file_path, sheet):
        """
        Beräkna matchlängd för valt blad och sätt max för vilotid (match_length - 1).
        """
        try:
            tabell = excel_to_text_string(file_path, sheet)
            match_length = calculate_match_length(tabell)
            max_rest = max(0, match_length - 1)
            # Uppdatera spinboxens "to"-värde
            self.rest_time_spinbox.config(to=max_rest)
            # Om nuvarande vilotid är större än max, justera ner den
            if self.rest_time_var.get() > max_rest:
                self.rest_time_var.set(max_rest)
        except Exception as e:
            # om något går fel, tillåt åtminstone 0-10
            self.rest_time_spinbox.config(to=10)
            messagebox.showwarning("Varning", f"Kunde inte bestämma matchlängd: {e}")

    def generate_outputs(self):
        file = self.file_path.get()
        sheet = self.sheet_var.get() or None
        rest_time = int(self.rest_time_var.get() or 0)
        if not file:
            messagebox.showwarning("Varning", "Välj en Excel-fil först!")
            return
        try:
            # Hämta tabellstext och matchlängd för validering innan skrivning
            tabell = excel_to_text_string(file, sheet)
            match_length = calculate_match_length(tabell)
            max_rest = max(0, match_length - 1)
            if rest_time > max_rest:
                messagebox.showwarning("Varning", f"Vald vilotid ({rest_time}) är för lång. Den sätts till max {max_rest} minuter.")
                rest_time = max_rest
                self.rest_time_var.set(rest_time)

            run_button(file, sheet, rest_time, out_dir=self.current_dir)
            messagebox.showinfo("Klart", f"Skapade tabell.html, tid.html och json.json i:\n{self.current_dir}")
        except Exception as e:
            messagebox.showerror("Fel", f"Något gick fel:\n{e}")


def excel_to_text_string(input_file, sheet_name=None):
    """
    Läser Excel-bladet och returnerar en tab-separerad text (inga headers).
    """
    xls = pd.ExcelFile(input_file, engine='openpyxl')
    if sheet_name is not None and sheet_name not in xls.sheet_names:
        available_sheets = ", ".join(xls.sheet_names)
        raise ValueError(f"Arket '{sheet_name}' finns inte. Tillgängliga ark: {available_sheets}")
    sheet_to_use = sheet_name if sheet_name else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sheet_to_use, header=None, dtype=str)
    return df.to_csv(sep='\t', index=False, header=False, encoding='utf-8')


def convert_to_html_table(input_text, match_length, rest_time):
    """
    Bygger tabell.html där tiderna skrivs som start-slut enligt (match_length - rest_time).
    """
    lines = [line for line in input_text.split('\n') if line.strip()]
    if not lines:
        return "<p>Ingen data</p>"
    headers = lines[0].split('\t')
    matches = []
    for line in lines[1:]:
        cols = line.split('\t')
        # säkerställ att vi har minst två kolumner
        if len(cols) < 2:
            continue
        matches.append({
            'match_num': cols[0].strip(),
            'time': cols[1].strip(),
            'mattor': [c for c in cols[2:]]
        })

    html_output = ['<table>']
    html_output.append('            <tr>')
    for header in headers:
        html_output.append(f'                <th>{header}</th>')
    html_output.append('            </tr>')

    for match in matches:
        try:
            start_dt = parse_time_str(match['time'])
        except Exception:
            # Om vi inte kan tolka starttid så hoppa över
            continue

        duration = match_length - rest_time
        if duration < 1:
            duration = match_length
        end_dt = start_dt + timedelta(minutes=duration)
        start_fmt = start_dt.strftime("%H:%M")
        end_fmt = end_dt.strftime("%H:%M")

        html_output.append(f'            <!-- Round {match["match_num"]} ({start_fmt}-{end_fmt}) -->')
        html_output.append('            <tr>')
        html_output.append(f'                <td>{match["match_num"]}</td>')
        html_output.append(f'                <td>{start_fmt}-{end_fmt}</td>')

        for matta in match['mattor']:
            cell_content = matta
            if isinstance(matta, str) and 'vs' in matta:
                participants = [p.strip() for p in matta.split('vs')]
                formatted_participants = []
                for participant in participants:
                    full_name = participant
                    if '(' in participant and ')' in participant:
                        name, club = participant.split('(', 1)
                        full_name = f"{name.strip()} ({club.strip(') ')})"
                    formatted = f'<a href="#" onclick="showSchedule(\'{full_name}\')">{full_name}</a>'
                    formatted_participants.append(formatted)
                cell_content = ' vs '.join(formatted_participants)
            html_output.append(f'                <td>{cell_content}</td>')
        html_output.append('            </tr>')

    html_output.append('</table>')
    return '\n'.join(html_output)


def parse_schedule(input_text, match_length, rest_time):
    """
    Skapar json-strukturen med personernas matcher och tider enligt match_length/rest_time.
    """
    schedule_data = {}
    lines = [line for line in input_text.split('\n') if line.strip()]
    if not lines:
        return json.dumps({}, ensure_ascii=False, indent=4)

    headers = [h.strip() for h in lines[0].split('\t')]
    num_mats = max(0, len(headers) - 2)

    for line in lines[1:]:
        cols = [col for col in line.split('\t')]  # behåll tomma kolumner
        if len(cols) < 2:
            continue
        match_num = cols[0].strip()
        time_str = cols[1].strip()
        try:
            start_dt = parse_time_str(time_str)
        except Exception:
            continue

        duration = match_length - rest_time
        if duration < 1:
            duration = match_length
        end_dt = start_dt + timedelta(minutes=duration)
        time_range = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"

        # bearbeta varje matta-kolumn
        for mat_idx in range(min(num_mats, max(0, len(cols) - 2))):
            match_str = cols[mat_idx + 2].strip() if len(cols) > mat_idx + 2 else ""
            if not match_str or 'vs' not in match_str:
                continue
            participants = [p.strip() for p in match_str.split('vs')]
            if len(participants) != 2:
                continue
            p1, p2 = participants
            for participant, opponent in [(p1, p2), (p2, p1)]:
                full_name = participant
                if '(' in participant and ')' in participant:
                    name, club = participant.split('(', 1)
                    full_name = f"{name.strip()} ({club.strip(') ')})"
                opp = opponent
                if '(' in opponent and ')' in opponent:
                    oname, oclub = opponent.split('(', 1)
                    opp = f"{oname.strip()} ({oclub.strip(') ')})"
                if full_name not in schedule_data:
                    schedule_data[full_name] = []
                schedule_data[full_name].append({
                    'match': match_num,
                    'time': time_range,
                    'opponent': opp,
                    'mat': f"Matta {mat_idx + 1}"
                })

    return json.dumps(schedule_data, indent=4, ensure_ascii=False)


def process_table_data(table_data):
    lines = [line for line in table_data.split('\n') if line.strip()]
    if not lines:
        return "<h2>Inga tider</h2>"
    headers = lines[0].split('\t')
    try:
        time_col_index = headers.index("Tid")
    except ValueError:
        return "Kolumnen 'Tid' hittades inte i tabellen."
    times = []
    for line in lines[1:]:
        cols = line.split('\t')
        if len(cols) > time_col_index:
            t = cols[time_col_index].strip()
            if t:
                try:
                    times.append(parse_time_str(t))
                except Exception:
                    pass
    if not times:
        return "Inga tider hittades i tabellen."
    times.sort()
    first_time = times[0]
    last_time = times[-1]
    if len(times) > 1:
        interval = times[1] - times[0]
        last_time = last_time + interval
    return f"<h2>{first_time.strftime('%H:%M')}-{last_time.strftime('%H:%M')}</h2>"


def run_button(excel, blad, rest_time, out_dir=None):
    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(__file__))

    tabell = excel_to_text_string(excel, blad)
    match_length = calculate_match_length(tabell)
    max_rest = max(0, match_length - 1)
    # säkerhetsklämning
    if rest_time > max_rest:
        rest_time = max_rest

    with open(os.path.join(out_dir, 'tabell.html'), 'w', encoding='utf-8') as f:
        f.write(convert_to_html_table(tabell, match_length, rest_time))

    with open(os.path.join(out_dir, 'json.json'), 'w', encoding='utf-8') as f:
        f.write(parse_schedule(tabell, match_length, rest_time))

    with open(os.path.join(out_dir, 'tid.html'), 'w', encoding='utf-8') as f:
        f.write(process_table_data(tabell))


if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelSheetSelector(root)
    root.mainloop()
