import http.server
import socketserver
import os
import time
import threading
import random
import json
import bcrypt
import mysql.connector as mysql
from dotenv import load_dotenv
# logging for debug messages on server console
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


load_dotenv()
HTTP_PORT = int(os.getenv('PORT', 8026))
SESS_COOKIE_NAME = "edswebsite-session-id"

print("starting server")

serverConnection = os.getenv('DB_SERVER')
user = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_DATABASE')
port = int(os.getenv('DB_PORT'))

# class for keeping track of active sessions
class ConnectedClient:
    def __init__(self, username, sessionID):
        self.username = username
        self.sessionID = sessionID
        self.lastActiveTime = time.time()
    
    def __str__(self):
        return f"username: {self.username}, sessionID: {self.sessionID}, lastActiveTime: {self.lastActiveTime}"
    def __repr__(self):
        return self.__str__()

    def update_last_active_time(self):
        self.lastActiveTime = time.time()

# go through all the images in the gear folder and keep a count of how many are in each folder
gearImages = {}
for folder, _, files in os.walk('assets/gear'):
    for file in files:
        if file.endswith('.png'):
            directory = os.path.basename(os.path.normpath(folder))
            if directory not in gearImages:
                gearImages[directory] = 0
            gearImages[directory] += 1
with open('assets/gear v2.json', 'r') as f:
    gearJson = json.load(f)


class Dungeon:
    def __init__(self, owner, level, seed, crystal):
        self.owner = owner
        self.level = level
        self.seed = seed
        self.crystal = crystal

        self.roomLayout = self.makeRoomLayout(seed, level, crystal)

    def __str__(self):
        return f"owner: {self.owner}, level: {self.level}, seed: {self.seed}, crystal: {str(self.crystal)}"
    def __repr__(self):
        return self.__str__()
    
    def gearAttrRoll(self, power, scale):
        return ((random.random()/5) + 0.9) * power * scale

    def rollGear(self, tier, extraDifficulty=0):
        itemElement = random.choices(list(self.crystal.keys()), weights=list(self.crystal.values()))[0]
        print(itemElement)
        itemType = random.choice(list(gearImages.keys()))
        statRolls = random.randint(1, 2) + random.randint(0, 1)*extraDifficulty + random.randint(0, 2)*tier
        power = int(3 * 1.4**self.level * (1 + 0.08*tier) * (1 + 0.05*extraDifficulty) * (0.85 + (0.01 * random.randint(-15, 45))))
        item = {"type": itemType, "picture": random.randint(0, gearImages[itemType]-1), "element": itemElement}
        # make the name
        item["name"] = ""
        if not random.randint(0, 2): item["name"] = random.choice(gearJson["names"]["prefixes"]) + " "
        item["name"] += gearJson["names"]["typeNames"][itemType]
        if not random.randint(0, 2): item["name"] += " of " + random.choice(gearJson["names"]["suffixes"])
        item["power"] = power

        # roll base stats
        for i in gearJson[itemType]["baseRolls"].keys():
            item[i] = round(self.gearAttrRoll(power, gearJson[itemType]["baseRolls"][i]),2)

        # roll extra stats
        for _ in range(statRolls):
            stat = random.choice(list(gearJson[itemType]["statRolls"].keys()))
            randRoll = self.gearAttrRoll(power, gearJson[itemType]["statRolls"][stat])
            if stat in item:
                item[stat] = round(max(item[stat], randRoll), 2)
            else:
                item[stat] = round(randRoll, 2)

        return item

    def tierRoll(tier, extraDifficulty=0):
        if extraDifficulty > 0:
            return max([random.choices([0, 1, 2], weights=tier)[0] for _ in range(extraDifficulty)])
        return random.choices([0, 1, 2], weights=tier)[0]
    
    def levelToTier(level):
        if level < 5: return (int(200/level), level, 0)
        return (int(200/level), level, int((level-1)/2))
    
    def makeRoomLayout(self, seed, level, crystal):
        rooms = [{"dungeonLevel": level, "type": "dungeonStart"}]
        random.seed(seed)
        tier = Dungeon.levelToTier(level)

        with open('assets/crystals.json') as f:
            crystalMonsters = json.load(f)["crystals"]
        with open('assets/monsters.json') as f:
            monsterJson = json.load(f)
        for i in range(random.randint(4,6 + level//5) + level//3):
            encounterType = random.choices(["puzzle", "fight", "trap", "hardFight"], weights=[1, 4, 1, 2])[0]
            tierRoll = Dungeon.tierRoll(tier)
            loot = [self.rollGear(tierRoll)] if not random.randint(0, 4) else []
            if encounterType == "puzzle" or encounterType == "trap":
                rooms.append({"type": encounterType, "difficulty": tierRoll})
            else:
                if not random.randint(0, 4): loot.append(self.rollGear(tierRoll))
                if encounterType == "hardFight":
                    tierRoll = Dungeon.tierRoll(tier, 3)
                    if not random.randint(0, 4): loot.append(self.rollGear(tierRoll, 1))
                monsterType = random.choices(list(crystal.keys()), weights=list(crystal.values()))[0]
                p = list(crystalMonsters[monsterType]["monsters"][["tier1", "tier2", "tier3"][tierRoll]].keys())
                w = list(crystalMonsters[monsterType]["monsters"][["tier1", "tier2", "tier3"][tierRoll]].values())
                monster = random.choices(p, weights=w)[0]
                monsters = []
                for m in monsterJson[monster]["spawnPattern"]:
                    if random.randint(1, 100) <= m["chance"]:
                        mAppend = monsterJson[m["name"]].copy()
                        del mAppend["spawnPattern"]
                        del mAppend["specialDrops"]
                        monsters.append(mAppend)

                rooms.append({"type": "fight", "difficulty": tierRoll, "monster": monsters, "loot": loot})

            
        return rooms

# dungeon = Dungeon("test", 10, random.random(), {"Fire": 10})


# [print((list(map(lambda x: print(x, end=" ") if x[0] not in ["picture", "name"] else (), list([(key, value) for key, value in dungeon.rollGear(1).items()])))) and "") for _ in range(20)]
# print(max([dungeon.rollGear(0)["power"] for _ in range(10000)]))

# dictionary of active sessions
sessions = {}

DB_CONN = mysql.connect(host=serverConnection,port=port,user=user,password=password,database=database)
# the meat and potatoes of the server
class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.DB_CONN = DB_CONN
        super().__init__(request, client_address, server)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*') 
        super().end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html' or self.path == '/home':
            self.path = '/pages/index.html'
        elif self.path.startswith('/game'):
            self.path = self.path.replace('/game', '/pages/game.html')
        super().do_GET()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        cookie_header = self.headers.get('Cookie')

        if cookie_header:
            cookie = cookie_header.split(';')
            for c in cookie:
                if c.strip().startswith(SESS_COOKIE_NAME) and c.strip().split('=')[1] in sessions:
                    session = c.strip().split('=')[1]
                    username = sessions[session].username
                    sessions[session].lastActiveTime = time.time()
                    break
        
        if self.path == '/upload_message':
            self.handle_upload_message(post_data, username)

        elif self.path == '/get_messages':
            self.get_messages()

        elif self.path == '/login':
            data = json.loads(post_data)
            self.login(data['username'], data['password'])
        
        elif self.path == '/get_SESS_cookie':
            self.send_response(200, SESS_COOKIE_NAME)
        
        elif self.path == '/get_basic_user_data':
            self.get_basic_user_data(username)
        
        elif self.path == '/set_held_crystals':
            data = json.loads(post_data)
            self.set_held_crystals(str(data['heldCrystals']), username)
        
        elif self.path == '/craft_crystals':
            data = json.loads(post_data)
            self.handle_crystal_craft(data, username)
        
        elif self.path == '/get_dungeon':
            self.get_dungeon(username)
        
        elif self.path == '/get_gear':
            self.get_gear(username)
        
        elif self.path == '/got_loot':
            data = json.loads(post_data)
            self.got_loot(data, username)
        
        elif self.path == '/equip_gear':
            data = json.loads(post_data)
            self.equip_gear(data, username)
        
        elif self.path == '/get_equipped_gear':
            self.get_equipped_gear(username)

    def get_equipped_gear(self, username):
        equipment = self.send_SQL_query('SELECT id, equipment FROM playerEquipment WHERE username = %s AND equipped = true', (username,), get=True, fetchAll=True)
        self.send_json_response(200, {'success': True, 'equipment': equipment})

    def equip_gear(self, data, username):
        print(data)
        equipped = list(int(x) for x in json.loads(data["equipped"]))
        print(equipped)
        self.send_SQL_query('UPDATE playerEquipment SET equipped = false WHERE username = %s', (username,))
        print((username, ", ".join(str(x) for x in equipped)))
        self.send_SQL_query(f'UPDATE playerEquipment SET equipped = true WHERE username = %s AND id IN ({", ".join(str(x) for x in equipped)})', (username, ))
        self.send_json_response(200, {'success': True})

    def got_loot(self, data, username):
        print(data)
        for loot in data['loot']:
            self.send_SQL_query('INSERT INTO playerEquipment (username, equipment) VALUES (%s, %s)', (username, json.dumps(loot)))
        self.send_json_response(200, {'success': True})

    def get_gear(self, username):
        gear = self.send_SQL_query('SELECT id, equipment, equipped FROM playerEquipment WHERE username = %s', (username,), get=True, fetchAll=True)
        print(gear)
        self.send_json_response(200, list([(x[0], json.loads(x[1]), x[2]) for x in gear]))

    def get_basic_user_data(self, username):
        tempPlayerData = self.send_SQL_query('SELECT * FROM basicPlayerData where username = %s', (username,), get=True, fetchAll=False)
        playerData = {'username':tempPlayerData[0], 'level':tempPlayerData[1], 'gold':tempPlayerData[2], 'heldCrystals':list(int(x) for x in tempPlayerData[4].replace("[", "").replace("]", "").split(","))}
        self.send_json_response(200, playerData)

    def upload_message(self, username, text):
        self.send_SQL_query('INSERT INTO messages (username, message, timestamp) VALUES (%s, %s, %s)', (username, text, int(time.time())))

    def get_messages(self):
        tempMessages = self.send_SQL_query('SELECT * FROM messages ORDER BY timestamp DESC LIMIT 50', (), get=True, fetchAll=True)[::-1]
        messages = [{'username': x[1], 'message': x[2], 'timestamp': x[3]} for x in tempMessages]
        self.send_json_response(200, {'messages': messages})

    def login(self, username, password):
        logger.info("Logging in as " + username)
        hashedPassword = bcrypt.hashpw((password).encode('utf-8'), bcrypt.gensalt())
        # Check if username already exists
        cursor = self.DB_CONN.cursor()
        try:
            cursor.execute('SELECT * FROM loginInfo WHERE username = %s', (username,))
            usernamePass = cursor.fetchone()
            if usernamePass is not None:
                # check if password is correct
                if not bcrypt.checkpw(password.encode('utf-8'), usernamePass[1].encode('utf-8')): 
                    self.send_json_response(400, {'error': 'Incorrect password'})
                    return 
                else: # login successful
                    sessionID = random.randbytes(32).hex()
                    sessions[str(sessionID)] = ConnectedClient(username, sessionID)
                    self.send_json_response(200, {'success': True, "session": sessionID}, {'Set-Cookie': f"{SESS_COOKIE_NAME}={sessionID}; HttpOnly"})
                    return 
            else: # new account creation
                print("making new account")
                cursor.execute('INSERT INTO loginInfo (username, password) VALUES (%s, %s)', (username, hashedPassword))
                self.DB_CONN.commit()
                self.send_SQL_query('INSERT INTO basicPlayerData (username, level, gold, current_dungeon, held_crystals) VALUES (%s, 1, 0, %s, "[0,0,0]")', (username, '{}'))
                self.send_SQL_query('INSERT INTO playerEquipment (username, equipment) VALUES (%s, %s)', (username, '{}'))
                # create a new session
                sessionID = random.randbytes(32).hex()
                sessions[str(sessionID)] = ConnectedClient(username, sessionID)
                self.send_json_response(200, {'success': True, "session": sessionID}, {'Set-Cookie': f"{SESS_COOKIE_NAME}={sessionID}; HttpOnly"})
        finally:
            cursor.close()

    def handle_upload_message(self, post_data, username):
            data = json.loads(post_data)
            if len(data['text']) > 1000:
                self.send_json_response(400, {'error': 'Message too long'})
                return
            try:
                self.upload_message(username, data['text'])
                self.send_json_response(200, {'success': True})
            except KeyError as e:
                logger.error(e)
                logger.info(data["session"])
                self.send_json_response(200, {'error': 'Invalid session'})

    def set_held_crystals(self, held_crystals, username):
        self.send_SQL_query('UPDATE basicPlayerData SET held_crystals = %s WHERE username = %s', (held_crystals, username))
        self.send_json_response(200, {'success': True})

    def handle_crystal_craft(self, data, username):
        crystalSeed = random.randint(0, 2**32 - 1)
        total_crystal_count = sum(data['crystalCounts'].values())
        if total_crystal_count % 100 != 0: 
            self.send_json_response(200, {'success': False, 'error': 'Not enough crystals'})
            return
        crystalPercents = {k: 100*round(v/total_crystal_count, 2) for k, v in data['crystalCounts'].items() if v > 0}
        crystalLevel = 0
        while total_crystal_count >= 100:
            total_crystal_count /= 2
            crystalLevel += 1
        dungeonString = str({"crystalPercents": crystalPercents, "crystalSeed": crystalSeed, "crystalLevel": crystalLevel})
        self.send_SQL_query('UPDATE basicPlayerData SET current_dungeon = %s WHERE username = %s', (dungeonString, username))
        self.send_json_response(200, {'success': True})

    def get_dungeon(self, username):
        tempPlayerData = self.send_SQL_query('SELECT current_dungeon FROM basicPlayerData WHERE username = %s', (username,), get=True, fetchAll=False)
        crystal = json.loads(tempPlayerData[0].replace("'", "\""))
        dungeon = Dungeon(username, crystal['crystalLevel'], crystal['crystalSeed'], crystal['crystalPercents'])
        self.send_json_response(200, dungeon.roomLayout)

    def send_json_response(self, status_code, data, extra_headers=None):
        self.send_response(status_code)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_SQL_query(self, query, params, get=False, fetchAll=True):
        try:
            cursor = self.DB_CONN.cursor()
            cursor.execute(query, params)
            if get:
                if fetchAll:
                    return cursor.fetchall()
                else:
                    return cursor.fetchone()
        finally:
            if not get:
                self.DB_CONN.commit()
            cursor.close()


def start_inactivity_check(timeout):
    inactivity_DB_CONN = mysql.connect(host=serverConnection,port=port,user=user,password=password,database=database)
    while True:
        for _ in range(100):
            # every minute check for inactive sessions
            logger.info("Checking inactive sessions...")
            logger.info(list(sessions.values()))
            current_time = time.time()
            inactive_sessions = [session_id for session_id, client in sessions.items() if current_time - client.lastActiveTime > timeout]
            
            for session_id in inactive_sessions:
                logger.info(f"Session {session_id} is inactive for too long. Removing user.")
                del sessions[session_id]
            
            time.sleep(60)

        # only once an hour check and delete guest accounts
        active_sessions = tuple(map(lambda x: x.username, list(sessions.values())))
        placeholders = ', '.join('%s' for _ in active_sessions)
        cursor = inactivity_DB_CONN.cursor()
        cursor.execute(f"DELETE FROM loginInfo WHERE username LIKE 'Guest%' AND username NOT IN ({placeholders})", active_sessions)
        cursor.execute(f"DELETE FROM basicPlayerData WHERE username LIKE 'Guest%' AND username NOT IN ({placeholders})", active_sessions)
        inactivity_DB_CONN.commit()


with http.server.HTTPServer(('', HTTP_PORT), CustomRequestHandler) as httpd:
    print(f"HTTP server serving at port {HTTP_PORT}")
    
    # Start inactivity check in a separate thread
    inactivity_thread = threading.Thread(target=start_inactivity_check, args=(3600,))
    inactivity_thread.daemon = True
    inactivity_thread.start()

    # Start the HTTP server
    httpd.serve_forever()
