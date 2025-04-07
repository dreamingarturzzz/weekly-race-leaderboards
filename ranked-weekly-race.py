import requests
import gspread
import os

players = dict()
currentWeek = requests.get("https://mcsrranked.com/api/weekly-race/").json()

if currentWeek["status"] != "success":
    print("request to mcsr ranked api returned a non-success status:")
    print(currentWeek)
    exit(1)
currentNumber = currentWeek["data"]["id"]

credentials = eval(os.environ["GOOGLE_CREDENTIALS"])

gc = gspread.service_account_from_dict(credentials)
sh = gc.open_by_key("1u0lakVQlJCWMwLNzAR3GoZWBcDVdzBe1gD1ZBb_ADbA")

# variable to force update even if the table is already up to date
# this should never be set to true under regular circumstances
bypass = False
lastUpdate = int(sh.worksheet("data").get("Z2")[0][0])

if not bypass and currentNumber - 1 <= lastUpdate:
    print("leaderboard already up to date")
    exit(0)
else:
    print("starting data requests")

for weekNumber in range(1, currentNumber):
    week = requests.get(f"https://mcsrranked.com/api/weekly-race/{weekNumber}").json()
    for completion in week["data"]["leaderboard"][:15]:
        player = completion["player"]
        uuid = player["uuid"]
        if uuid not in players:
            players[uuid] = {
                "username": player["nickname"],
                "country": player["country"],
                "top1Badges": 0,
                "top1Earliest": None,
                "top1Rank": None,
                "top1Weeks": [],
                "top5Badges": 0,
                "top5Earliest": None,
                "top5Rank": None,
                "top5Weeks": [],
                "top10Badges": 0,
                "top10Earliest": None,
                "top10Rank": None,
                "top10Weeks": [],
                "top15Badges": 0,
                "top15Earliest": None,
                "top15Rank": None,
                "top15Weeks": [],
                "bestPlacement": 16,
                "bestPlacementCount": 0,
                "bestPlacementEarliest": [],
                "allPoints": {i: "-" for i in range(1, currentNumber)},
                "totalPoints": 0
            }

        rank = completion["rank"]
        badgeType = 0
        if 11 <= rank <= 15:
            badgeType = 15
        elif 6 <= rank:
            badgeType = 10
        elif 2 <= rank:
            badgeType = 5
        else:
            badgeType = 1

        if rank == 1:
            score = 30
        elif rank == 2:
            score = 20
        elif rank == 3:
            score = 15
        elif rank <= 5:
            score = 10
        elif rank <= 10:
            score = 6
        else:
            score = 3
        players[uuid]["totalPoints"] += score
        players[uuid]["allPoints"][weekNumber] = score

        players[uuid][f"top{badgeType}Badges"] += 1
        if players[uuid][f"top{badgeType}Earliest"] is None:
            players[uuid][f"top{badgeType}Earliest"] = weekNumber
            players[uuid][f"top{badgeType}Rank"] = rank
        players[uuid][f"top{badgeType}Weeks"].append(weekNumber)
        if rank == players[uuid]["bestPlacement"]:
            players[uuid]["bestPlacementCount"] += 1
            players[uuid]["bestPlacementEarliest"].append(weekNumber)
        elif rank < players[uuid]["bestPlacement"]:
            players[uuid]["bestPlacement"] = rank
            players[uuid]["bestPlacementCount"] = 1
            players[uuid]["bestPlacementEarliest"] = [weekNumber]

    print(f"week {weekNumber} calculated")


for uuid in players.keys():
    top5True = players[uuid]["top1Badges"] + players[uuid]["top5Badges"]
    top10True = players[uuid]["top10Badges"] + top5True
    top15True = players[uuid]["top15Badges"] + top10True
    top5TrueEarliest = players[uuid]["top5Earliest"]
    top10TrueEarliest = players[uuid]["top10Earliest"]
    top15TrueEarliest = players[uuid]["top15Earliest"]
    top5TrueRank = players[uuid]["top5Rank"]
    top10TrueRank = players[uuid]["top10Rank"]
    top15TrueRank = players[uuid]["top15Rank"]

    if players[uuid]["top1Earliest"] is not None:
        if top5TrueEarliest is None or top5TrueEarliest > players[uuid]["top1Earliest"]:
            top5TrueEarliest = players[uuid]["top1Earliest"]
            top5TrueRank = players[uuid]["top1Rank"]
    players[uuid]["top5True"] = top5True
    players[uuid]["top5TrueEarliest"] = top5TrueEarliest
    players[uuid]["top5TrueRank"] = top5TrueRank

    if players[uuid]["top5TrueEarliest"] is not None:
        if top10TrueEarliest is None or top10TrueEarliest > players[uuid]["top5TrueEarliest"]:
            top10TrueEarliest = players[uuid]["top5TrueEarliest"]
            top10TrueRank = players[uuid]["top5TrueRank"]
    players[uuid]["top10True"] = top10True
    players[uuid]["top10TrueEarliest"] = top10TrueEarliest
    players[uuid]["top10TrueRank"] = top10TrueRank

    if players[uuid]["top10TrueEarliest"] is not None:
        if top15TrueEarliest is None or top15TrueEarliest > players[uuid]["top10TrueEarliest"]:
            top15TrueEarliest = players[uuid]["top10TrueEarliest"]
            top15TrueRank = players[uuid]["top10TrueRank"]
    players[uuid]["top15True"] = top15True
    players[uuid]["top15TrueEarliest"] = top15TrueEarliest
    players[uuid]["top15TrueRank"] = top15TrueRank

print("starting tab updates")
sh.worksheet("data").batch_clear(["A3:Z10000"])
sh.worksheet("data").update([[i["username"],
                              i["top1Badges"], i["top1Earliest"],
                              i["top5True"], i["top5TrueEarliest"], i["top5TrueRank"],
                              i["top5Badges"], i["top5Earliest"], i["top5Rank"],
                              i["top10True"], i["top10TrueEarliest"], i["top10TrueRank"],
                              i["top10Badges"], i["top10Earliest"], i["top10Rank"],
                              i["top15True"], i["top15TrueEarliest"], i["top15TrueRank"],
                              i["top15Badges"], i["top15Earliest"], i["top15Rank"],
                              i["bestPlacement"], i["bestPlacementCount"], i["country"]] for i in players.values()],
                            "A3")

print("finished updating data tab")

# champion tab
for tier in range(1):
    sheet = 1
    data = [[i["username"], i[f"top{sheet}Badges"], *i[f"top{sheet}Weeks"]] for i in players.values() if i[f"top{sheet}Badges"] != 0]

    rows = 1 + len(data)
    columns = 3 + max([i[1] for i in data])
    ws = sh.worksheet(f"Top {sheet}")
    ws.resize(rows, columns)
    ws.batch_clear([f"A2:ZZ{rows}"])
    ws.merge_cells("D1:ZZ1")
    data.sort(key=lambda x: (-x[1], x[2]))
    for i in data:
        for j in range(2, len(i)):
            i[j] = f"W{i[j]}"
    ws.update_cell(1, 4, "")
    ws.update([[i + 1, *data[i]] for i in range(rows - 1)], "A2")
    ws.columns_auto_resize(3, columns - 1)
    ws.update_cell(1, 4, f"All top {sheet} badges")
    print(f"finished updating champion tab")

# true top x tab
for tier in range(1, 4):
    sheet = tier * 5
    data = [[i["username"], i[f"top{sheet}True"], i[f"top{sheet}TrueEarliest"], i[f"top{sheet}TrueRank"]] for i in players.values() if i[f"top{sheet}True"] != 0]
    rows = 1 + len(data)
    columns = 4
    ws = sh.worksheet(f"Top {sheet}")
    ws.resize(rows, columns)
    ws.batch_clear([f"A2:D{rows}"])
    data.sort(key=lambda x: (-x[1], x[2], x[3]))
    for i in data:
        i[2] = f"W{i[2]} - #{i[3]}"
        del i[3]
    ws.update([[i + 1, *data[i]] for i in range(rows - 1)], "A2")
    print(f"finished updating true top {sheet} tab")

# top x badge tab
for tier in range(1, 4):
    sheet = tier * 5
    data = [[i["username"], i[f"top{sheet}Badges"], i[f"top{sheet}Earliest"], i[f"top{sheet}Rank"], *i[f"top{sheet}Weeks"]] for i in players.values() if i[f"top{sheet}Badges"] != 0]
    rows = 1 + len(data)
    columns = 4 + max([i[1] for i in data])
    ws = sh.worksheet(f"Top {sheet} badges")
    ws.resize(rows, columns)
    ws.batch_clear([f"A2:ZZ{rows}"])
    ws.merge_cells("E1:ZZ1")
    data.sort(key=lambda x: (-x[1], x[2], x[3]))
    for i in data:
        i[2] = f"W{i[2]} - #{i[3]}"
        del i[3]
        for j in range(3, len(i)):
            i[j] = f"W{i[j]}"
    ws.update_cell(1, 5, "")
    ws.update([[i + 1, *data[i]] for i in range(rows - 1)], "A2")
    ws.columns_auto_resize(4, columns - 1)
    ws.update_cell(1, 5, f"All top {sheet} badges")
    print(f"finished updating top {sheet} badges tab")

# best placements tab
ws = sh.worksheet("Best placements")
data = [[i["username"], i["bestPlacement"], i["bestPlacementCount"], *i["bestPlacementEarliest"]] for i in players.values()]
data.sort(key=lambda x: (x[1], -x[2], x[3]))
rows = len(data) + 1
columns = 0
for i in data:
    columns = max(columns, i[2])
    i[1] = f"#{i[1]}, {i[2]} time{"s" if i[2] > 1 else ""}"
    del i[2]
    for j in range(2, len(i)):
        i[j] = f"W{i[j]}"
columns += 3
ws.resize(rows, columns)
ws.batch_clear([f"A2:ZZ{rows}"])
ws.merge_cells("D1:ZZ1")
ws.update_cell(1, 4, "")
ws.update([[i + 1, *data[i]] for i in range(rows - 1)], "A2")
ws.columns_auto_resize(3, columns - 1)
ws.update_cell(1, 4, "Weeks with that placement")
print("finished updating best placements tab")


def maxAndEarliest(record):
    mx = 0
    earliest = 0
    cnt = 0
    for i in range(currentNumber - 1):
        if record[i] == "-":
            continue
        if record[i] > mx:
            mx = record[i]
            earliest = i
            cnt = 0
        if record[i] == mx:
            cnt += 1
    return -mx, -cnt, earliest


# points leaderboard
data = [[i["username"], *i["allPoints"].values(), i["totalPoints"]] for i in players.values()]
data.sort(key=lambda x: (-x[-1], *maxAndEarliest(x[1:-1])))
ws = sh.worksheet("Points leaderboard (WIP)")
lastWeek = int(ws.get("1:1")[0][-2][1:])
if lastWeek < currentNumber - 1:
    ws.insert_cols([[f"W{i}"] for i in range(lastWeek + 1, currentNumber)], lastWeek + 3, inherit_from_before=True)
ws.columns_auto_resize(2, 1 + currentNumber)
ws.batch_clear([f"A2:ZZ{rows}"])
values = [[i + 1, *data[i]] for i in range(rows - 1)]
for i in range(1, len(values)):
    if values[i - 1][-1] == values[i][-1]:
        values[i][0] = values[i - 1][0]
ws.update(values, "A2")
print("finished updating points tab")
sh.worksheet("data").update_cell(2, 26, currentNumber - 1)
print("\nleaderboards updated")
