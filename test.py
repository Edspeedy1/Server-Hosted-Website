import random
import json

class Dungeon:
    def __init__(self, owner, level, seed, crystal):
        self.owner = owner
        self.level = level
        self.seed = seed
        self.crystal = crystal

        self.roomLayout = self.makeRoomLayout(seed, level, crystal)

    def tierRoll(tier, extraDifficulty=1):
        m = 0
        for _ in range(extraDifficulty):
            m = max(m, random.choices(list(range(3)), weights=tier)[0])
        return m

    def levelToTier(level):
        if level < 5: return (int(200/level), level, 0)
        return (int(200/level), level, int((level-1)/2))
    
    def makeRoomLayout(self, seed, level, crystal):
        rooms = []
        random.seed(seed)
        tier = Dungeon.levelToTier(level)

        with open('assets/crystals.json') as f:
            crystalMonsters = json.load(f)["crystals"]
        for _ in range(random.randint(4, 6 + level//5) + level):
            encounterType = random.choices(["puzzle", "fight", "trap", "hardFight"], weights=[1, 4, 1, 2])[0]
            tierRoll = Dungeon.tierRoll(tier)
            if encounterType == "puzzle" or encounterType == "trap":
                rooms.append({"type": encounterType, "difficulty": tierRoll})
            else:
                if encounterType == "hardFight":
                    tierRoll = Dungeon.tierRoll(tier, 3)
                monsterType = random.choices(list(crystal.keys()), weights=list(crystal.values()))[0]
                w = list(crystalMonsters[monsterType]["monsters"][["tier1", "tier2", "tier3"][tierRoll]].values())
                p = list(crystalMonsters[monsterType]["monsters"][["tier1", "tier2", "tier3"][tierRoll]].keys())
                monster = random.choices(p, weights=w)[0]

                rooms.append({"type": encounterType, "difficulty": tierRoll, "monster": monster})
        return rooms

for i in range(15):
    d = Dungeon("test", 10, i, {"Fire": 10, "Nature": 3})
    list(map(lambda x: print(x["type"].ljust(15), end="  ") if x["type"] != "fight" and x["type"] != "hardFight" else print(x['monster'].ljust(15), end="  "), d.roomLayout))
    print()