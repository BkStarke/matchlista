# -*- coding: utf-8 -*-
import random
import math
from collections import defaultdict

def read_participants_from_text(text):
    groups = {}
    for line in text.strip().splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 3:
            name, club, group = parts[0].strip(), parts[1].strip(), parts[2].strip()
            first_name = name.split()[0] if name.split() else name
            formatted = f"{first_name} ({club})"
            groups.setdefault(group, []).append(formatted)
    return groups

def round_robin_schedule(participants):
    parts = participants[:]
    if len(parts) < 2:
        return []
    if len(parts) % 2 == 1:
        parts.append("BYE")
    n = len(parts)
    schedule = []
    for _ in range(n - 1):
        matches = []
        for i in range(n // 2):
            p1, p2 = parts[i], parts[n - 1 - i]
            if p1 != "BYE" and p2 != "BYE":
                matches.append((p1, p2))
        schedule.append(matches)
        parts = [parts[0]] + [parts[-1]] + parts[1:-1]
    return schedule

def find_k_per_group_dp(groups, q, r):
    """
    Hitta antal deltagare per grupp som ska få +1 (k_g) så att:
      - varje k_g har samma parity som needed för att göra group sum even
      - sum k_g == r
    Returnerar dict group->k or None om ingen lösning.
    """
    group_list = list(groups.keys())
    sizes = [len(groups[g]) for g in group_list]
    p = [ (q * s) % 2 for s in sizes ]  # required parity for k_g

    # DP: dp[i][s] = store chosen k's up to group i yielding sum s
    dp = {0: []}  # sum->list of k values (for processed groups)
    for idx, g in enumerate(group_list):
        s_g = sizes[idx]
        start = p[idx]
        options = list(range(start, s_g + 1, 2))  # k values with correct parity
        new_dp = {}
        for acc_sum, chosen in dp.items():
            for opt in options:
                new_sum = acc_sum + opt
                if new_sum > r:
                    continue
                if new_sum not in new_dp:
                    new_dp[new_sum] = chosen + [opt]
        dp = new_dp
        if not dp:
            return None  # ingen möjlighet att fortsätta
    if r not in dp:
        return None
    chosen_list = dp[r]  # lista av k_g i samma ordning som group_list
    return {group_list[i]: chosen_list[i] for i in range(len(group_list))}

def realize_group_matches(participants, deg_target):
    """
    Realisera en multigraph (lista av matcher) inom gruppen så att varje perso
    får exakt deg_target[p] matcher. Vi tillåter upprepade par (multiedges).
    """
    matches = []
    # working copy
    rem = dict(deg_target)
    # sanity
    total_deg = sum(rem.values())
    if total_deg % 2 != 0:
        raise ValueError("Summa grader i gruppen är inte jämn — bör inte hända.")
    # fast loop
    # Use greedy Havel-Hakimi-like but allow repetitions: always pair highest-degree node with highest-degree other
    while True:
        # get participants with rem>0
        positives = [(p, d) for p, d in rem.items() if d > 0]
        if not positives:
            break
        positives.sort(key=lambda x: -x[1])
        u, du = positives[0]
        # pair u du times
        for _ in range(du):
            # find v != u with maximal rem
            candidates = [(p, d) for p, d in rem.items() if p != u and d > 0]
            if not candidates:
                # if there's no other with d>0, but sum of rem should be 2*k; we can pair with someone and increase their degree
                # as fallback pick any other participant (with zero) and allow them to be paired (will decrement from zero -> negative not allowed)
                # but proper construction should avoid this situation; throw informative error
                raise RuntimeError("Realiseringsfel: kunde inte hitta partner i gruppen. Detta borde ej hända.")
            candidates.sort(key=lambda x: -x[1])
            v, dv = candidates[0]
            matches.append((u, v))
            rem[u] -= 1
            rem[v] -= 1
    return matches

def generate_exact_matches(groups, target_total):
    """
    Huvudfunktion:
      - beräkna q och r
      - hitta vilka som får q+1 via DP (så per-grupp parity OK)
      - realisera matcher per grupp enligt dessa grader
    Return: matches_list, counts_dict, target_per_person_float
    """
    participants_all = [p for plist in groups.values() for p in plist]
    N = len(participants_all)
    if N == 0:
        return [], {}, 0.0

    twoT = 2 * target_total
    q = twoT // N
    r = twoT - q * N  # antal deltagare som ska få q+1 grader
    target_per_person_float = twoT / N

    # försök hitta k_g per group via DP
    k_per_group = find_k_per_group_dp(groups, q, r)
    if k_per_group is None:
        # Om DP misslyckas, använd fallback: försök en mild heuristisk fördelning
        # (vi försöker ändå ge så jämt som möjligt — detta händer mycket sällan)
        k_per_group = {}
        remaining = r
        for g, plist in groups.items():
            take = min(len(plist), remaining)
            k_per_group[g] = take
            remaining -= take
        # om fortfarande remaining > 0, fördela +1 extra slumpvis
        if remaining > 0:
            all_groups = list(groups.keys())
            i = 0
            while remaining > 0:
                g = all_groups[i % len(all_groups)]
                if k_per_group[g] < len(groups[g]):
                    k_per_group[g] += 1
                    remaining -= 1
                i += 1

    # bygg target grader per person
    deg_targets = {}
    for g, plist in groups.items():
        s = len(plist)
        k = k_per_group.get(g, 0)
        # välj k deltagare i gruppen som får q+1 (förutsatt att s>0)
        chosen = plist.copy()
        random.shuffle(chosen)
        chosen = chosen[:k]
        for p in plist:
            deg_targets[p] = q + (1 if p in chosen else 0)

    # kontroll: sum degrees == 2*target_total ?
    sumdeg = sum(deg_targets.values())
    if sumdeg != twoT:
        # om differens pga DP-fallback, justera genom att lägga eller ta bort 1 från slumpvalda deltagare
        diff = twoT - sumdeg
        if diff > 0:
            # ge +1 till diff slumpmässiga deltagare (men hålles nära)
            ppl = list(deg_targets.keys())
            random.shuffle(ppl)
            idx = 0
            while diff > 0:
                deg_targets[ppl[idx % len(ppl)]] += 1
                idx += 1
                diff -= 1
        elif diff < 0:
            ppl = sorted(deg_targets.keys(), key=lambda x: deg_targets[x], reverse=True)
            idx = 0
            diff = -diff
            while diff > 0 and idx < len(ppl):
                if deg_targets[ppl[idx]] > 0:
                    deg_targets[ppl[idx]] -= 1
                    diff -= 1
                idx += 1
            if diff > 0:
                # sista utväg: justera från anyone
                ppl2 = list(deg_targets.keys())
                i = 0
                while diff > 0:
                    deg_targets[ppl2[i % len(ppl2)]] -= 1
                    i += 1
                    diff -= 1

    # nu realisera matcherna per grupp
    all_matches = []
    for g, plist in groups.items():
        targets = {p: deg_targets[p] for p in plist}
        # sanity: gruppsum even
        if sum(targets.values()) % 2 != 0:
            # justera genom att flytta en +1 internt (sällsynt)
            for p in plist:
                targets[p] += 1
                break
        group_matches = realize_group_matches(plist, targets)
        all_matches.extend(group_matches)

    # slutkontroll — antal matcher
    if len(all_matches) != target_total:
        # Om något avviker (borde inte hända), trimma eller fyll med slumpmatch från pool
        if len(all_matches) > target_total:
            all_matches = all_matches[:target_total]
        else:
            pool = [m for g in groups.values() for m in ([(a,b) for a in g for b in g if a!=b])]
            while len(all_matches) < target_total:
                all_matches.append(random.choice(pool))

    # räkna ut counts
    counts = defaultdict(int)
    for a,b in all_matches:
        counts[a] += 1
        counts[b] += 1

    return all_matches, counts, target_per_person_float

def arrange_matches(all_matches):
    """Ordna matchlistan så inte samma person går två gånger i rad och sprid ut så gott det går."""
    if not all_matches:
        return []
    arranged = []
    remaining = all_matches.copy()
    random.shuffle(remaining)
    players = set(p for m in all_matches for p in m)
    cooldown = {p: 0 for p in players}
    while remaining:
        if arranged:
            last = arranged[-1]
            banned = {last[0], last[1]}
            candidates = [m for m in remaining if m[0] not in banned and m[1] not in banned]
        else:
            candidates = remaining
        if not candidates:
            candidates = remaining
        best = max(candidates, key=lambda m: min(cooldown.get(m[0],0), cooldown.get(m[1],0)))
        arranged.append(best)
        remaining.remove(best)
        for p in cooldown:
            cooldown[p] += 1
        cooldown[best[0]] = 0
        cooldown[best[1]] = 0
    return arranged

def main():
    print("Klistra in texten från Excel (Namn<TAB>Klubb<TAB>Grupp). Avsluta med en tom rad + ENTER.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line)
    text = "\n".join(lines)

    groups = read_participants_from_text(text)
    if not groups:
        print("Inga deltagare hittades. Kontrollera inputformatet.")
        return

    # skriv gruppinfo
    total_unique = 0
    participants_all = [p for plist in groups.values() for p in plist]
    print("\n📊 Gruppinfo:")
    for g, plist in groups.items():
        base = round_robin_schedule(plist)
        unique = [m for rnd in base for m in rnd]
        per_round = len(base[0]) if base else 0
        print(f"- Grupp {g}: {len(plist)} deltagare → {per_round} matcher per runda, {len(unique)} unika matcher")
        total_unique += len(unique)
    print(f"Totalt deltagare: {len(participants_all)}, totala unika matcher (alla grupper): {total_unique}\n")

    # fråga mål
    while True:
        try:
            target_total = int(input("Hur många matcher vill du ha totalt? "))
            if target_total < 0:
                print("Ange ett icke-negativt heltal.")
                continue
            break
        except ValueError:
            print("Ange ett heltal, t.ex. 50.")

    matches, counts, tpp = generate_exact_matches(groups, target_total)
    arranged = arrange_matches(matches)

    print(f"\n🎯 Målsättning per person (teoretisk): ≈ {tpp:.3f} matcher/person")
    print(f"Totalt genererade matcher: {len(arranged)} (mål {target_total})\n")

    print("📋 Matcher (alla grupper blandade):")
    for i, (a, b) in enumerate(arranged, 1):
        print(f"{a} vs {b}")

    # statistik per deltagare
    all_names = [p for plist in groups.values() for p in plist]
    counts_map = {p: counts.get(p, 0) for p in all_names}
    minc = min(counts_map.values())
    maxc = max(counts_map.values())
    print(f"\nℹ️ Matcher per deltagare — spridning: min {minc}, max {maxc} (skillnad {maxc-minc})")
    for g, plist in groups.items():
        print(f" Grupp {g}:")
        for p in plist:
            print(f"  {p}: {counts_map[p]}")

if __name__ == "__main__":
    main()
    input()