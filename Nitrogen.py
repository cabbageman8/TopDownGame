# Nitrogen Alpha 0.00

# to compile; run
# py -m nuitka --standalone --include-data-dir=data=data --include-data-dir=save=save Nitrogen.py

# to build Docker image of server; run
# docker build -t cabbageman/nitrogenserver .
import random

import pygame
from pygame.locals import *
from PIL import Image
import pickle
from math import pi, tau, sin, cos, tan, asin, acos, atan2, ceil, floor, sqrt, log
import cProfile
from quadtree import root_node
from glrenderer import glrenderer
import sys
import os
import time
import socket
import base64
from objects import *

logfile = open("log.txt", 'w')
sys.stderr = logfile
sys.stdout = logfile

pygame.init()
pygame.font.init()
pygame.joystick.init()

print("number of gamepads:", pygame.joystick.get_count())
gamepads = []
for i in range(pygame.joystick.get_count()):
    joystick = pygame.joystick.Joystick(i)
    joystick.init()
    gamepads.append(joystick)

clock = pygame.time.Clock()
text = ["Connecting to server"]

try: os.mkdir("save")
except: pass
try:
    sav = open(os.path.join("save", "settings.txt"), 'r')
    txt = sav.read()
    sav.close()
except FileNotFoundError:
    txt = '''# maximum frames per second
FPS = 60

# window size used for windowed mode and screenshot size
window_size = 1920, 1080

# enable fullscreen at launch
fullscreen = True

# players with the same spawn key will spawn in the same place (remove or rename your savedata file to spawn as new character)
spawnkey = worldspawn

# vertical synchronisation
vsyncenabled = True

# tile size effects the scale of gameplay objects
tile_size = 75

# font size effects the scale of ui elements
fontsize = 45

# ip address of game server
ip = server.cabbage.moe

# udp port number of game server
port = 27448
'''
    sav = open(os.path.join("save", "settings.txt"), 'w')
    sav.write(txt)
    sav.close()
    text.append('could not find settings file, defaults loaded')

txt = txt.replace(" ", "").replace("\n\n", '\n').replace("\n\n", '\n')
txt = {line.split('=')[0] : line.split('=')[1] for line in txt.split('\n') if len(line) > 0 and line[0] != '#'}
print(txt)
FPS = int(txt["FPS"])
window_size = (int(txt["window_size"].split(',')[0]), int(txt["window_size"].split(',')[1]))
fullscreen = txt["fullscreen"] != "False"
spawnkey = txt["spawnkey"]
vsyncenabled = txt["vsyncenabled"] != "False"
tile_size = int(txt["tile_size"])
fontsize = int(txt["fontsize"])
ip = txt["ip"]
port = int(txt["port"])

hud_size = (2560, 1440)

pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)
pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)

pygame.display.set_mode(size=window_size, flags=DOUBLEBUF|OPENGL, vsync=vsyncenabled)

if fullscreen:
    pygame.display.toggle_fullscreen()
    window_size = pygame.display.get_window_size()

silombol = pygame.font.Font(os.path.join("data", "SilomBol.ttf"), fontsize)
silombol2 = pygame.font.Font(os.path.join("data", "SilomBol.ttf"), fontsize*2)
textures_img = []
texd = {}

def load_textures():
    global texd
    global textures_img
    textures_img = []
    for mat in textures:
        file = Image.open(os.path.join("data", mat + ".png")).convert("RGBA")
        frame_list = []
        for i in range(file.height//file.width):
            frame = pygame.image.fromstring( file.crop(Rect(0,file.width*i,file.width,file.width*(i+1))).resize([128, 128], resample=Image.NEAREST).tobytes(), [128, 128], "RGBA").convert_alpha()
            frame_list.append(len(textures_img))
            textures_img.append(frame)
        texd.update({mat : frame_list})
        file.close()

    for e in entities:
        file = Image.open(os.path.join("data", "entities", e+".png")).convert("RGBA")
        fileb = Image.open(os.path.join("data", "entities", e+"45.png")).convert("RGBA")
        for i in range(4):
            frame_list = []
            for j in range(file.height // file.width):
                frame = pygame.image.fromstring( file.crop(Rect(0, file.width * j, file.width, file.width * (j + 1))).resize([128, 128], resample=Image.NEAREST).rotate(90*i).tobytes(), [128, 128], "RGBA").convert_alpha()
                frame_list.append(len(textures_img))
                textures_img.append(frame)
            texd.update({e+str(i*2): frame_list})
            frame_list = []
            for j in range(fileb.height // fileb.width):
                frame = pygame.image.fromstring( fileb.crop(Rect(0, fileb.width * j, file.width, file.width * (j + 1))).resize([128, 128], resample=Image.NEAREST).rotate(90*i).tobytes(), [128, 128], "RGBA").convert_alpha()
                frame_list.append(len(textures_img))
                textures_img.append(frame)
            texd.update({e+str(i*2+1): frame_list})
        file.close()
        fileb.close()
load_textures()
def get_tex(name, index):
    return texd[name][int(index)%len(texd[name])]

texpack = pygame.Surface((min(128*128, 128*(len(textures_img))), 128*(1+len(textures_img)//128)), flags=pygame.SRCALPHA).convert_alpha()
for i, m in enumerate(textures_img):
    texpack.blit(m, (128*(i%128),128*(i//128)))
pygame.image.save(texpack, "texpack.png")
overlay = pygame.Surface(hud_size).convert_alpha()

Renderer = glrenderer(texpack, overlay)
Renderer.ctx.screen.viewport = (0, 0, *window_size)

def draw_text(surface, xy, t, has_bg=0):
    if has_bg:
        pygame.draw.rect(surface, (255, 255, 255, 128), pygame.Rect((xy[0]-3, xy[1]), silombol.size(t)))
    surface.blit(silombol.render(t, True, (0, 0, 0)), xy)

def get_alias(name):
    alias = name if name not in OBJ.keys() or "alias" not in OBJ[name].keys() else OBJ[name]["alias"]
    alias = alias if name not in ITEMS.keys() or "alias" not in ITEMS[name].keys() else ITEMS[name]["alias"]
    alias = alias if name not in TILES.keys() or "alias" not in TILES[name].keys() else TILES[name]["alias"]
    return alias
def get_description(name):
    description = "" if name not in OBJ.keys() or "description" not in OBJ[name].keys() else OBJ[name]["description"]
    description = description if name not in ITEMS.keys() or "description" not in ITEMS[name].keys() else ITEMS[name]["description"]
    description = description if name not in TILES.keys() or "description" not in TILES[name].keys() else TILES[name]["description"]
    return description

menu = 1
def construct_overlay():
    global text
    global overlay
    global Renderer
    overlay.fill((0, 0, 0, 0))
    if menu == 0 or menu == 2: # game play hud
        overlay.blit(textures_img[texd["selection"][0]], (0, 128 * selected_item_slot - 128 * 4.5 + overlay.get_size()[1] / 2))
        for i in range(9):
            if hotbar[i][0] != None and hotbar[i][2] > 0:
                overlay.blit(textures_img[texd[hotbar[i][0]][0]], (0, 128 * i - 128 * 4.5 + overlay.get_size()[1] / 2))
                draw_text(overlay, (10, 128 * i - 128 * 4.5 + overlay.get_size()[1] / 2), str(hotbar[i][2]), has_bg=True)
        slot = hotbar[int(selected_item_slot)]
        if slot[0] == "debug":
            for x,y in list_tiles_on_screen(8):
                tile_coords = [ceil(screen_coords[0] / tile_size) + x - 1,
                               ceil(screen_coords[1] / tile_size) + y - 1]
                climate = get_climate(tile_coords[0], tile_coords[1])
                overlay.blit(silombol2.render(str(int(climate[0]))+','+str(int(climate[1]))+','+str(int(climate[2]))+','+str(int(100/(climate[2]/30)-climate[1])), True, (0, 0, 0)), (x*tile_size, y*tile_size+(x*32+16)%tile_size))
        if slot[0] != None and slot[2] > 0 and menu == 0:
            draw_text(overlay, (100, 128 * selected_item_slot - 128 * 4.5 + overlay.get_size()[1] / 2), get_alias(str(slot[0])), has_bg=True)
    if menu == 1: # title screen / help menu
        file = Image.open(os.path.join("data", "titlescreen.png")).convert("RGBA")
        bgimg = pygame.image.fromstring(file.resize(overlay.get_size(), resample=Image.NEAREST).tobytes(),
                                      overlay.get_size(), "RGBA").convert_alpha()
        overlay.blit(bgimg, (0, 0))
        for i, t in enumerate(text):
            overlay.blit(silombol.render(t, True, (0, 0, 0)), (128, 128+silombol.size(t)[1] * i))
    if menu == 2: # crafting menu
        file = Image.open(os.path.join("data", "craftingmenu.png")).convert("RGBA")
        bgimg = pygame.image.fromstring(file.resize(overlay.get_size(), resample=Image.NEAREST).tobytes(),
                                      overlay.get_size(), "RGBA").convert_alpha()
        overlay.blit(bgimg, (0, 0))
        pygame.draw.rect(overlay, (255, 255, 255, 128), pygame.Rect((128, 128 * selected_crafting_slot - 128 * 4.5 + overlay.get_size()[1] / 2), (280, 128)))
        for i, product in enumerate(crafting.keys()):
            overlay.blit(textures_img[texd[product[1]][0]], (128, 128 * i - 128 * 4.5 + overlay.get_size()[1] / 2))
            draw_text(overlay, (256, 128 * i - 128 * 4.5 + overlay.get_size()[1] / 2), get_alias(product[1]), has_bg=True)
        selected_recipe = tuple(crafting.keys())[selected_crafting_slot]
        draw_text(overlay, (650, 0-128 * 4.5 + overlay.get_size()[1] / 2), get_alias(selected_recipe[1]), has_bg=True)
        draw_text(overlay, (650+128, 1*fontsize - 128 * 4.5 + overlay.get_size()[1] / 2), item_type_map[selected_recipe[2]], has_bg=True)
        draw_text(overlay, (650+128, 2*fontsize - 128 * 4.5 + overlay.get_size()[1] / 2), get_description(selected_recipe[1]), has_bg=True)

        overlay.blit(textures_img[texd[selected_recipe[1]][0]], (650, 1*fontsize - 128 * 4.5 + overlay.get_size()[1] / 2))
        draw_text(overlay, (650, 1*fontsize - 128 * 4.5 + overlay.get_size()[1] / 2), str(selected_recipe[0]), has_bg=True)
        draw_text(overlay, (650, 4*fontsize-128 * 4.5 + overlay.get_size()[1] / 2), "Requires:", has_bg=True)
        for i, item in enumerate(crafting[selected_recipe]["materials"]):
            overlay.blit(textures_img[texd[item[1]][0]], (650+128*i, 5*fontsize - 128 * 4.5 + overlay.get_size()[1] / 2))
            draw_text(overlay, (660+128*i, 5*fontsize - 128 * 4.5 + overlay.get_size()[1] / 2), str(item[0]), has_bg=True)
        if "workstation" in crafting[selected_recipe].keys():
            draw_text(overlay, (650, 8 * fontsize - 128 * 4.5 + overlay.get_size()[1] / 2), "Workstation:", has_bg=True)
            for i, wrk in enumerate(crafting[selected_recipe]["workstation"]):
                phrase = ""
                for j, item in enumerate(wrk):
                    if j == 0:
                        if i > 0:
                            phrase += "or "
                    else:
                        phrase += " and "
                    phrase += item
                draw_text(overlay, (700, (i+9) * fontsize - 128 * 4.5 + overlay.get_size()[1] / 2), phrase, has_bg=True)
        for i, t in enumerate(text):
            overlay.blit(silombol.render(t, True, (0, 0, 0)), (overlay.get_size()[0]-silombol.size(t)[0]-64, silombol.size(t)[1] * i - 128 * 4.5 + overlay.get_size()[1] / 2))
    Renderer.update_overlay(overlay)
    if len(text)*fontsize > window_size[1]:
        text = []
construct_overlay()
Renderer.render((0, 0), tile_size)
pygame.display.flip()

pygame.mixer.music.load('data/ambience.wav')
pygame.mixer.music.play(-1)
shovel_sfx = pygame.mixer.Sound('data/shovel.wav')
shovel_sfx.set_volume(0.5)
grass_step_sfx = pygame.mixer.Sound('data/grass-step.wav')
grass_step_sfx.set_volume(0.2)
hit_sfx = pygame.mixer.Sound('data/hit.wav')
hit_sfx.set_volume(0.5)
fish_sfx = pygame.mixer.Sound('data/fish.wav')
fish_sfx.set_volume(0.2)
seasplash_sfx = pygame.mixer.Sound('data/seasplash.wav')
seasplash_sfx.set_volume(0.2)
crumple_sfx = pygame.mixer.Sound('data/crumple.wav')
crumple_sfx.set_volume(0.5)
jump_into_water_sfx = pygame.mixer.Sound('data/jump-into-water.wav')
jump_into_water_sfx.set_volume(0.2)

def seeded_random(a):
    output = (41406202+14874235*a     )%79493069
    output = (43915416+77751829*output)%76741089
    output = (66947287+44145130*output)%90370934
    output = (64705634+34405431*output)%23928528
    output = (24300417+80810414*output)%10000
    return output/10000
p2r_cache = {}
def point_to_random(x, y):
    if (x,y) in p2r_cache:
        return p2r_cache[(x,y)]
    r = seeded_random(seeded_random(x) + seeded_random(y))
    p2r_cache.update({(x,y) :r})
    if len(p2r_cache) > 2**16:
        p2r_cache.clear()
    return r

server_address = (ip, port)

# Create socket for server
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
sock.setblocking(False)

text = ["Visit cabbage.moe", "Nitrogen Alpha", "WASD for movement", "ESC for save and quit", "F4 for fullscreen", "Scroll to select item", "LM destroy selected", "RM place from hotbar", "Press C to craft", "Press H to exit help menu"]
# get local data
try:
    sav = open(os.path.join("save", "savedata.pickle"), 'r')
    data = pickle.loads(base64.b64decode(sav.read()))
    pos = data['pos']
    hotbar = data['hotbar']
    player_number = data['player_number']
    sav.close()
    text.append('Loaded local save')
except FileNotFoundError:
    spawn = seeded_random(int.from_bytes(spawnkey.encode('utf-8'), "big"))
    pos = [10**10-spawn*10**10*2+pi, 10**10-seeded_random(spawn)*10**10*2+tau]
    hotbar = [["candle", 1,1], [None, 0,0], [None, 0,0], [None, 0,0], [None, 0,0], [None, 0,0], [None, 0,0], [None, 0,0], [None, 0,0]]
    player_number = int(seeded_random(time.time()%100000000)*10000)
    sav = open(os.path.join("save", "savedata.pickle") , 'wb')
    data = {'pos': pos, 'hotbar': hotbar, 'player_number':player_number}
    sav.write(base64.b64encode(pickle.dumps(data)))
    sav.close()
    text.append('could not find local save, blank save loaded')

screen_coords = [pos[0] * tile_size - window_size[0] // 2, pos[1] * tile_size - window_size[1] // 2]
# get server data
map = root_node()
try:
    sock.sendto('world_download '.encode('utf-8'), server_address)
    downl_time = time.time()
    world_data = []
    while time.time() - downl_time < 1:
        try:
            byt, address = sock.recvfrom(2**16)
            print("received", len(byt), "bytes")
            world_data.append(byt)
        except BlockingIOError:
            pass
    for byt in world_data:
        data = pickle.loads(byt)
        for key, value in data.items():
            payload = (key, value)
            map.apply_data(payload[0][0], payload[0][1], payload[1])
        print("loaded", len(data), "tiles")
    del world_data
    text.append('loaded save from server')
except ConnectionResetError:
    text.append('could not reach server')
    text.append('progress will not be saved')
except socket.gaierror:
    text.append('the ip you have entered is not valid')
    text.append('progress will not be saved')
except pickle.UnpicklingError:
    text.append('data received is not valid, the server or client is likely out of date')
    text.append('progress will not be saved')

#hotbar = [["treestump", 1, 1], ["treestump", 1, 1], ["birchtreestump", 1, 1], ["treestump", 1, 1], ["wall", 1, 1000], ["tiles", 1, 1000], ["dirt", 0, 1], ["lushundergrowth", 0, 1], ["bottlebrushdirt", 0, 1]]
hotbar[8] = ["farmland", 0, 999]
#hotbar[1] = ["candle", 1, 999]
#hotbar[1] = ["teabush", 1, 2]
#hotbar[2] = ["chiliseeds", 1, 999]
#hotbar[3] = ["soybeans", 1, 999]
print("hotbar:", hotbar)
def save_game():
    print("saving game")
    sav = open(os.path.join("save", "savedata.pickle"), 'wb')
    data = {'pos': pos, 'hotbar': hotbar, 'player_number':player_number}
    sav.write(base64.b64encode(pickle.dumps(data)))
    sav.close()
    if len(map.save_buffer) > 0:
        sock.sendto(str('save_to_server '+str(base64.b64encode(pickle.dumps(map.save_buffer)))).encode('utf-8'), server_address)
        map.save_buffer.clear()
selected_item_slot = 0
selected_crafting_slot = 0

construct_overlay()

last_climate = (None, None, None)
biome_size = 100
def get_climate(x, y):
    global last_climate
    if last_climate[0] == x and last_climate[1] == y:
        return last_climate[2]
    else:
        x /= biome_size
        y /= biome_size
        temp     = ((sin(0.70688 * y) * sin(0.08321 * y) * sin(1.20191 * y + 1.07952 * x) + cos(1.83391 * x / 5 - 1.00643 * y / 5) * cos(0.27705 * x / 5))/2+0.5)
        moisture = ((sin(0.56554 * y) * sin(0.49491 * y) * sin(1.63167 * y + 1.36682 * x) + cos(1.19063 * x / 7 - 1.52815 * y / 7) * cos(0.13701 * x / 7))/2+0.5)
        altitude = ((sin(0.48967 * y/2) * sin(0.32156 * y/2) * sin(1.78655 * y/2 + 1.68442 * x/2) + cos(1.18567 * x / 9 - 1.36988 * y / 9) * cos(0.15346 * x / 9))/2+0.5)
        temp, moisture, altitude = max(0.001, min(0.999, temp))*35+10, max(0.001, min(0.999, moisture))*75, max(0.001, min(0.999, altitude))*100
        last_climate = (x, y, (temp, moisture, altitude))
        return temp, moisture, altitude
last_biome = (None, None, None)
def get_biome(x, y):
    global last_biome
    if last_biome[0] == x and last_biome[1] == y:
        return last_biome[2]
    else:
        temp, moisture, altitude = get_climate(x, y)
        if altitude < 20:
            return biomes[8]
        biome_num = biome_map[int(temp/45*4)][int(moisture/100*6)]
        biome = biomes[biome_num]
        last_biome = (x,y, biome)
        return biome
def get_local(temp, moisture, altitude, biome):
    return biome[1][int(len(biome[1]) * point_to_random(int(temp / 45 * len(biome[1]))+int(altitude / 130 * len(biome[1])), int(moisture / 100 * len(biome[1]))))]

def get_mat(x, y):
    local = max(-1, min(1, sin(0.546354 * y/5) * sin(0.876964 * y/5) * sin(1.45638 * y/5 + 1.82266 * x/5) + cos(1.94367 * x/5 - 1.743247 * y/5) * cos(0.869632 * x/5) ))
    biome = get_biome(x, y)
    temp, moisture, altitude = get_climate(x, y)
    if temp % 10 > 9 and moisture % 10 > 9 and altitude < 40 and altitude > 20:
        # is in structure
        if x%5==0 or y%4==0:
            mat = "hexpavers"
        else:
            mat = "farmland"
    else:
        mat_list = get_local(temp, moisture, altitude, biome)
        mat = mat_list[int((local+1)/2*(len(mat_list)-1))]
    return mat

def decorate(x, y, mat):
    dec = None
    r = point_to_random(x, y)
    r2 = seeded_random(r)
    if mat == "hexpavers":
        if r < 0.4:
            dec = "hexpavers"
    else:
        if r > 0.0:
            dec = list(OBJ)[int(r2*len(OBJ))]
            temp, moisture, altitude = get_climate(x, y)
            salinity = max(0, 100 / (altitude / 30) - moisture)
            if "plant" in OBJ[dec]["flags"]:
                if "native" in OBJ[dec]["flags"]:
                    if mat not in OBJ[dec]["substrate"] or \
                            temp < OBJ[dec]["temperiture"][0] or temp > OBJ[dec]["temperiture"][1] or \
                            moisture < OBJ[dec]["moisture"][0] or moisture > OBJ[dec]["moisture"][1] or \
                            salinity > OBJ[dec]["salinity"][1] or salinity < OBJ[dec]["salinity"][0]:
                        dec = None
                elif mat == "farmland":
                    if r < 0.4:
                        dec = None
                else:
                    dec = None
            elif r < 0.4 or "substrate" not in OBJ[dec].keys() or mat not in OBJ[dec]["substrate"] or\
                    "salinity" in OBJ[dec].keys() and (salinity > OBJ[dec]["salinity"][1] or salinity < OBJ[dec]["salinity"][0]):
                dec = None
    if dec == None:
        map.cache_data(int(x), int(y), (mat, ))
    else:
        map.cache_data(int(x), int(y), (mat, dec))
    return dec

def get_tile_info(x, y):
    map_data = map.get_data(int(x), int(y))
    if map_data:
        return tuple(map_data+(None,)*7)[:7]
    mat = get_mat(x, y)
    dec = decorate(x, y, mat)
    tile_data = (mat, dec)
    return tuple(tile_data+(None,)*7)[:7]

def list_tiles_on_screen(dist):
    # returns an generator for every tile near the screen in order of manhattan distance
    screen_size = floor((window_size[0]/tile_size)/2), floor((window_size[1]/tile_size)/2)
    radius = ceil( screen_size[0] + screen_size[1] + dist )
    for i in reversed(range(radius)):
        for j in range(i-1):
            a, b = i-j-1, j
            if a <= screen_size[0]+dist and b <= screen_size[1]+dist:
                yield screen_size[0] + a, screen_size[1] + b
                yield screen_size[0] + a, screen_size[1] - b-1
            if b <= screen_size[0]+dist and a <= screen_size[1]+dist:
                yield screen_size[0] - b, screen_size[1] + a-1
                yield screen_size[0] - b, screen_size[1] - a

def screen_transform(x, y, z, w, h, tex, sway):
    # convert pixel coords to shader coords
    return (x/window_size[0]*2,
            y/window_size[1]*2,
            z,
            w/window_size[0]*2,
            h/window_size[1]*2,
            tex, sway)

def geom_light(x, y, z, w, h, hue):
    # return element for lighting using tile coords
    global screen_coords
    return (( -1+(1 - screen_coords[0] % tile_size + tile_size * (x + abs(w) // 2 + 0.5) - screen_coords[0] // tile_size * tile_size) / window_size[0] * 2,
              +1-(1 - screen_coords[1] % tile_size + tile_size * (y + abs(h) // 2 + 0.5) - screen_coords[1] // tile_size * tile_size) / window_size[1] * 2,
            1), hue)

def geom_tile(x, y, z, tex, sway):
    # return element for rendering a tile using int tile coords relitive to the screen
    global screen_coords
    return screen_transform((1 - screen_coords[0] % tile_size + tile_size * x),
                            (1 - screen_coords[1] % tile_size + tile_size * y),
                            z,
                            tile_size,
                            tile_size,
                            tex, sway)

def geom_object(x, y, z, w, h, tex, sway):
    # return element for rendering a texture using int tile coords relitive to the world
    global screen_coords
    return screen_transform((1 - screen_coords[0] % tile_size + tile_size * (x - w / 2 + 0.5) - screen_coords[0] // tile_size * tile_size),
                            (1 - screen_coords[1] % tile_size + tile_size * (y - h / 2 + 0.5) - screen_coords[1] // tile_size * tile_size),
                            z,
                            w * tile_size,
                            h * tile_size,
                            tex, sway)
def draw_object(tex, x, y, z, w, h, sway):
    Renderer.vert_list.append(geom_object(x, y, z, w, h, tex, sway))
    if w * h == 0:
        Renderer.reflection_list.append(geom_object(x, y, -z, w, h, tex, sway))
def draw_object_foreground(tex, x, y, z, w, h, sway):
    Renderer.foreground_list.append(geom_object(x, y, 1+z, w, h, tex, sway))
    Renderer.reflection_list.append(geom_object(x, y, -z, w, h, tex, sway))
def draw_shadow(tex, x, y, z, w, h, sway):
    Renderer.reflection_list.append(geom_object(x, y, -z, w, h, tex, sway))
    Renderer.shadow_list.append(geom_object(x, y, -z, w, h, tex, sway))
def draw_weather(tex, x, y, z, w, h, sway):
    Renderer.weather_list.append(geom_object(x, y, 1+z, w, h, tex, sway))

velocity = [0, 0]
acceleration = 1/300

keydown_set = set()
gamepad_set = set()
old_gamepad_set = set()
mouse_pos = pygame.mouse.get_pos()
def handle_keys():
    global running
    global mouse_pos
    global old_gamepad_set
    mouse_rel = pygame.mouse.get_rel()
    if mouse_rel[0] + mouse_rel[1]:
        mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game()
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                save_game()
                running = False
            keydown_set.add(event.key)
            if (event.key in (pygame.K_F2, pygame.K_h, pygame.K_c)):
                keydown_set.add("press"+str(event.key))
        elif event.type == pygame.KEYUP and event.key not in (pygame.K_F4, ):
            keydown_set.remove(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            keydown_set.add("mouse"+str(event.button))
            if (event.button in (1,)):
                keydown_set.add("click"+str(event.button))
        elif event.type == pygame.MOUSEBUTTONUP:
            keydown_set.remove("mouse"+str(event.button))
            if (event.button in (4, 5)):
                keydown_set.add("unclick"+str(event.button))
    old_gamepad_set = set(gamepad_set)
    gamepad_set.clear()
    for g in gamepads:
        for a in range(g.get_numaxes()):
            state = g.get_axis(a)
            if abs(state) > 0.333:
                if a == 0:
                    gamepad_set.add("stickx"+str(floor(state)*+2+1))
                elif a == 1:
                    gamepad_set.add("sticky"+str(floor(state)*-2-1))
                elif a == 3:
                    mouse_pos = [mouse_pos[0]+state*7, mouse_pos[1]]
                    if mouse_pos[0] < 0 or mouse_pos[0] > window_size[0]:
                        mouse_pos = [mouse_pos[0] - state * 7, mouse_pos[1]]
                elif a == 4:
                    mouse_pos = [mouse_pos[0], mouse_pos[1]+state*7]
                    if mouse_pos[1] < 0 or mouse_pos[1] > window_size[1]:
                        mouse_pos = [mouse_pos[0], mouse_pos[1] - state * 7]
        for b in range(g.get_numbuttons()):
            state = g.get_button(b)
            if state:
                gamepad_set.add("button"+str(b))
        for d in range(g.get_numhats()):
            x, y = g.get_hat(d)
            if x:
                gamepad_set.add("d-padx"+str(x))
            if y:
                gamepad_set.add("d-pady"+str(y))

# selected data in map format ie: mat, dec, age, item, count, roof, enc
def find_destination_slot(item, item_type):
    first_blank = None
    destination_item_slot = int(selected_item_slot)
    for i in range(9):
        if item == hotbar[destination_item_slot][0] and hotbar[destination_item_slot][1] == item_type and hotbar[destination_item_slot][2] > 0:
            break
        elif first_blank == None and hotbar[destination_item_slot][2] == 0:
            first_blank = destination_item_slot
        destination_item_slot = (destination_item_slot + 1) % 9
    if item != hotbar[destination_item_slot][0] and first_blank != None:
        destination_item_slot = first_blank
    if hotbar[destination_item_slot][2] == 0 or (item == hotbar[destination_item_slot][0] and hotbar[destination_item_slot][1] == item_type):
        return destination_item_slot
    return None

running=True
curtime = pygame.time.get_ticks()
char_direction = 0
char_speed = 0
char_anim = 0
steptime = curtime
world_text = {}
player_text = {}
last_server_update = 0
last_random_tick = 0
server_fails = 0
selected_tile = [0, 0]
player_tile_info = get_tile_info(ceil(pos[0] - 1), ceil(pos[1] - 1))

def handle_controls(dt):
    global velocity
    global curtime
    global tile_size
    global screen_coords
    global selected_tile
    global char_direction
    global overlay
    global window_size
    global selected_item_slot
    global steptime
    global char_anim
    global world_text
    global player_text
    global last_server_update
    global last_random_tick
    global server_fails
    global pos
    global player_tile_info
    global menu
    # interpret inputs
    if pygame.K_w in keydown_set or "sticky1" in gamepad_set:
        if pygame.K_a in keydown_set or "stickx-1" in gamepad_set:
            velocity[0] -= acceleration * 0.707106781187
            velocity[1] -= acceleration * 0.707106781187
            char_direction = 3
        elif pygame.K_d in keydown_set or "stickx1" in gamepad_set:
            velocity[0] += acceleration * 0.707106781187
            velocity[1] -= acceleration * 0.707106781187
            char_direction = 1
        else:
            velocity[1] -= acceleration
            char_direction = 0
    elif pygame.K_s in keydown_set or "sticky-1" in gamepad_set:
        if pygame.K_a in keydown_set or "stickx-1" in gamepad_set:
            velocity[0] -= acceleration * 0.707106781187
            velocity[1] += acceleration * 0.707106781187
            char_direction = 5
        elif pygame.K_d in keydown_set or "stickx1" in gamepad_set:
            velocity[0] += acceleration * 0.707106781187
            velocity[1] += acceleration * 0.707106781187
            char_direction = 7
        else:
            velocity[1] += acceleration
            char_direction = 4
    else:
        if pygame.K_a in keydown_set or "stickx-1" in gamepad_set:
            velocity[0] -= acceleration
            char_direction = 2
        elif pygame.K_d in keydown_set or "stickx1" in gamepad_set:
            velocity[0] += acceleration
            char_direction = 6
    if "press"+str(pygame.K_h) in keydown_set:
        if menu == 0:
            menu = 1
        else:
            menu = 0
        construct_overlay()
        keydown_set.remove("press"+str(pygame.K_h))
    if "press"+str(pygame.K_c) in keydown_set:
        if menu == 0:
            menu = 2
        else:
            menu = 0
        construct_overlay()
        keydown_set.remove("press"+str(pygame.K_c))
    if pygame.K_F4 in keydown_set:
        pygame.display.toggle_fullscreen()
        window_size = pygame.display.get_window_size()
        Renderer.ctx.screen.viewport = (0, 0, *window_size)
        overlay = pygame.Surface(hud_size).convert_alpha()
        construct_overlay()
        keydown_set.remove(pygame.K_F4)
    if pygame.K_F9 in keydown_set:
        pos = [10**10-seeded_random(pos[0])*10**10*2+pi, 10**10-seeded_random(pos[1])*10**10*2+tau]

    #player_tile_info = get_tile_info(ceil(pos[0] - 1), ceil(pos[1] - 1))
    new_player_tile_info = get_tile_info(ceil(pos[0] - 1 + dt * velocity[0]), ceil(pos[1] - 1 + dt * velocity[1]))
    if (player_tile_info[1] in OBJ.keys() and "solid" in OBJ[player_tile_info[1]]["flags"]):
        pos[1] += 1
        velocity = [0, 0]
    else:
        if (not "water" in player_tile_info[0]) and "water" in new_player_tile_info[0]:
            jump_into_water_sfx.stop()
            jump_into_water_sfx.play()
        if (new_player_tile_info[1] in OBJ.keys() and "solid" in OBJ[new_player_tile_info[1]]["flags"]):
            velocity = [0, 0]
        else:
            if (player_tile_info[0] in difficult_terrain or new_player_tile_info[1] in OBJ.keys() and "slow" in OBJ[new_player_tile_info[1]]["flags"]):
                dnom = 2
            else:
                dnom = 3
            velocity[0] -= velocity[0] / dnom
            velocity[1] -= velocity[1] / dnom
            pos[0] += dt * velocity[0]
            pos[1] += dt * velocity[1]
    player_tile_info = new_player_tile_info
    screen_coords = [pos[0] * tile_size - window_size[0] // 2, pos[1] * tile_size - window_size[1] // 2]
    selected_tile = [mouse_pos[0] + screen_coords[0] % tile_size,
                     mouse_pos[1] + screen_coords[1] % tile_size]
    selected_tile = [-screen_coords[0] % tile_size + tile_size * ceil(selected_tile[0] / tile_size) - window_size[0] // 2,
                     -screen_coords[1] % tile_size + tile_size * ceil(selected_tile[1] / tile_size) - window_size[1] // 2]
    selected_tile = [ceil(pos[0] + ceil(selected_tile[0] / tile_size) - 3),
                     ceil(pos[1] + ceil(selected_tile[1] / tile_size) - 3)]
    selected_data = get_tile_info(*selected_tile)
    if "click1" in keydown_set or "button8" in gamepad_set and not "button8" in old_gamepad_set:
        if Rect(0, window_size[1] / 2 - 128 * 4.5, 128, 128*9).collidepoint(mouse_pos):
            selected_item_slot = (mouse_pos[1]-(window_size[1] / 2 - 128 * 4.5))//128
        else:
            if selected_data != None and len(selected_data) > 3 and selected_data[3] != None:
                # grab item from selected tile
                item_num = 1 if len(selected_data) <= 4 else selected_data[4]
                destination_item_slot = find_destination_slot(selected_data[3], 2)
                if destination_item_slot != None:
                    crumple_sfx.play()
                    hotbar[destination_item_slot] = [selected_data[3], 2, hotbar[destination_item_slot][2] + item_num]
                    print("picked up item such that:", hotbar[destination_item_slot])
                    map.set_data(*selected_tile, selected_data[:3] + (None, None) + selected_data[5:])
            elif selected_data != None and len(selected_data) > 1 and selected_data[1] != None:
                # grab decoration from selected tile
                drops = 0 if "drops" not in OBJ[selected_data[1]] else OBJ[selected_data[1]]["drops"]
                if drops:
                    drop_num, dropped_item, dropped_item_type = drops
                else:
                    drop_num, dropped_item, dropped_item_type = 1, selected_data[1], 1
                destination_item_slot = find_destination_slot(dropped_item, dropped_item_type)
                if hotbar[destination_item_slot][2] == 0 or drops == None or (dropped_item == hotbar[destination_item_slot][0] and hotbar[destination_item_slot][1] == dropped_item_type):
                    shovel_sfx.play()
                    if drops != None:
                        hotbar[destination_item_slot] = [dropped_item, dropped_item_type, hotbar[destination_item_slot][2] + drop_num]
                    leaves = None if "leaves" not in OBJ[selected_data[1]] else OBJ[selected_data[1]]["leaves"]
                    map.set_data(*selected_tile, (selected_data[0], leaves, int(time.time()))+selected_data[3:])
            else:
                destination_item_slot = find_destination_slot(selected_data[0], 0)
                if destination_item_slot != None:
                    # grab material from selected tile
                    shovel_sfx.play()
                    hotbar[destination_item_slot] = [selected_data[0], 0, hotbar[destination_item_slot][2] + 1]
                    biome = get_biome(*selected_tile)
                    temp, moisture, altitude = get_climate(*selected_tile)
                    map.set_data(*selected_tile, (get_local(temp, moisture, altitude, biome)[0], )+selected_data[1:])
        construct_overlay()
        if "click1" in keydown_set:
            keydown_set.remove("click1")
    if "mouse2" in keydown_set:
        if len(selected_data) >= 4:
            destination_item_slot = find_destination_slot(selected_data[3], 2)
        elif len(selected_data) >= 2:
            destination_item_slot = find_destination_slot(selected_data[1], 1)
        else:
            destination_item_slot = find_destination_slot(selected_data[0], 0)
        selected_item_slot = selected_item_slot if destination_item_slot == None else destination_item_slot
        construct_overlay()
    if "mouse3" in keydown_set or "button9" in gamepad_set:
        if hotbar[int(selected_item_slot)][2] > 0:
            if hotbar[int(selected_item_slot)][1] == 2:
                # place item in selected tile
                crumple_sfx.play()
                age = None if len(selected_data) < 3 else selected_data[2]
                map.set_data(*selected_tile, (selected_data[0], selected_data[1], age) + (hotbar[int(selected_item_slot)][0], hotbar[int(selected_item_slot)][2]) + selected_data[5:])
                hotbar[int(selected_item_slot)][2] = 0
            elif (selected_data[1] == None and hotbar[int(selected_item_slot)][1] == 1 and
                    ("plant" not in OBJ[hotbar[int(selected_item_slot)][0]]["flags"] or
                      selected_data[0] in OBJ[hotbar[int(selected_item_slot)][0]]["substrate"] )):
                # place decoration in selected tile
                crumple_sfx.play()
                map.set_data(*selected_tile, (selected_data[0], hotbar[int(selected_item_slot)][0], int(time.time())) + selected_data[3:])
                hotbar[int(selected_item_slot)][2] -= 1
            elif hotbar[int(selected_item_slot)][1] == 0 and selected_data[0] != hotbar[int(selected_item_slot)][0]:
                # place material in selected tile
                hit_sfx.play()
                map.set_data(*selected_tile, (hotbar[int(selected_item_slot)][0],) + selected_data[1:])
                hotbar[int(selected_item_slot)][2] -= 1
            construct_overlay()
    if "unclick4" in keydown_set or "d-pady1" in gamepad_set and not "d-pady1" in old_gamepad_set:
        selected_item_slot = (selected_item_slot-1)%9
        construct_overlay()
        if "unclick4" in keydown_set:
            keydown_set.remove("unclick4")
    if "unclick5" in keydown_set or "d-pady-1" in gamepad_set and not "d-pady-1" in old_gamepad_set:
        selected_item_slot = (selected_item_slot+1)%9
        construct_overlay()
        if "unclick5" in keydown_set:
            keydown_set.remove("unclick5")

def handle_controls_crafting(dt):
    global selected_crafting_slot
    global menu
    global hotbar
    global text
    if "click1" in keydown_set or "button8" in gamepad_set and not "button8" in old_gamepad_set:
        if Rect(128, window_size[1] / 2 - 128 * 4.5, 280, 128*9).collidepoint(mouse_pos):
            selected_crafting_slot = int((mouse_pos[1]-(window_size[1] / 2 - 128 * 4.5))//128)%len(crafting)
        construct_overlay()
        if "click1" in keydown_set:
            keydown_set.remove("click1")
    if "press"+str(pygame.K_h) in keydown_set:
        menu = 0
        construct_overlay()
        keydown_set.remove("press"+str(pygame.K_h))
    if "press"+str(pygame.K_c) in keydown_set:
        menu = 0
        construct_overlay()
        keydown_set.remove("press"+str(pygame.K_c))

    if pygame.K_SPACE in keydown_set:
        old_hotbar = [slot.copy() for slot in hotbar]
        hotbar_items = [item for item, type, count in hotbar]
        selected_recipe = tuple(crafting.keys())[selected_crafting_slot]
        try:
            for count, item in crafting[selected_recipe]["materials"]:
                if item in hotbar_items and hotbar[hotbar_items.index(item)][2] >= count:
                    hotbar[hotbar_items.index(item)][2] -= count
                else:
                    raise Exception("insufficent items")
            destination_item_slot = find_destination_slot(selected_recipe[1], selected_recipe[2])
            if destination_item_slot != None:
                crumple_sfx.play()
                hotbar[destination_item_slot] = [selected_recipe[1], selected_recipe[2], hotbar[destination_item_slot][2] + selected_recipe[0]]
            else:
                raise Exception("no free slots in hotbar")
        except Exception as e:
            hotbar = old_hotbar
            if text[-1] == str(e):
                del text[-1]
            else:
                text.append(str(e))
        construct_overlay()
    if "unclick4" in keydown_set or "d-pady1" in gamepad_set and not "d-pady1" in old_gamepad_set:
        selected_crafting_slot = int(selected_crafting_slot-1)%len(crafting)
        construct_overlay()
        if "unclick4" in keydown_set:
            keydown_set.remove("unclick4")
    if "unclick5" in keydown_set or "d-pady-1" in gamepad_set and not "d-pady-1" in old_gamepad_set:
        selected_crafting_slot = int(selected_crafting_slot+1)%len(crafting)
        construct_overlay()
        if "unclick5" in keydown_set:
            keydown_set.remove("unclick5")

def handle_controls_help(dt):
    global menu
    if "press"+str(pygame.K_h) in keydown_set:
        menu = 0
        construct_overlay()
        keydown_set.remove("press"+str(pygame.K_h))
    if "press"+str(pygame.K_c) in keydown_set:
        menu = 0
        construct_overlay()
        keydown_set.remove("press"+str(pygame.K_c))

def main():
    global velocity
    global curtime
    global tile_size
    global screen_coords
    global selected_tile
    global char_direction
    global overlay
    global window_size
    global selected_item_slot
    global steptime
    global char_anim
    global text
    global world_text
    global player_text
    global last_server_update
    global last_random_tick
    global server_fails
    global pos
    global player_tile_info
    global menu
    dt = pygame.time.get_ticks() - curtime
    curtime = pygame.time.get_ticks()
    handle_keys()
    if menu == 0:
        handle_controls(dt)
    elif menu == 1:
        handle_controls_help(dt)
    elif menu == 2:
        handle_controls_crafting(dt)
    # start loading the world into renderer
    for x, y in list_tiles_on_screen(8):
        height = 0.0
        tile_coords = [ceil(screen_coords[0] / tile_size) + x - 1,
                       ceil(screen_coords[1] / tile_size) + y - 1]
        tile_data = get_tile_info(*tile_coords)
        mat = tile_data[0]
        index = int(point_to_random(tile_coords[0], tile_coords[1]) * 1000)
        if (mat in animated):
            matindex = int(index+(curtime//200+tile_coords[0]*tile_coords[0]+tile_coords[1]))
        elif (mat == "hexpavers"):
            matindex = int(tile_coords[0]*13 + tile_coords[1] * tile_coords[1]*7)*2+tile_coords[0]
        else:
            matindex = index
        Renderer.tile_list.append(geom_tile(x, y, height, get_tex(mat, matindex), 0))

        decor = tile_data[1]
        if decor in OBJ.keys():
            model = OBJ[decor]["model"]
            size = OBJ[decor]["size"]
            if model == "tree" or model == "doubletree" or model == "qtree":
                if "solid" in OBJ[decor]["flags"]:
                    log = "treelog"
                    if "log" in OBJ[decor].keys():
                        log = OBJ[decor]["log"]
                    draw_object(get_tex(log, index), tile_coords[0], tile_coords[1], 0.01, 1, 1, 0)
                height = OBJ[decor]["height"](tile_coords[0], tile_coords[1])
                trunk = "treetrunk"
                if "trunk" in OBJ[decor].keys():
                    trunk = OBJ[decor]["trunk"]
                draw_object(get_tex(trunk, 1), tile_coords[0], tile_coords[1], height, 0, 1, 0)
                draw_object(get_tex(trunk, 0), tile_coords[0], tile_coords[1], height, 1, 0, 0)
                if "solid" in OBJ[decor]["flags"]:
                    stump = "treestump"
                    if "stump" in OBJ[decor].keys():
                        stump = OBJ[decor]["stump"]
                    draw_object(get_tex(stump, 0), tile_coords[0], tile_coords[1], height, 1, 1, 0)
                if model == "doubletree":
                    draw_object_foreground(get_tex(decor, tile_coords[0]+10*tile_coords[1]), tile_coords[0], tile_coords[1], height/2, size*((1+tile_coords[0])%2*2-1), size*((1+tile_coords[1])%2*2-1), 1)
                if model == "qtree":
                    draw_object(           get_tex(decor, tile_coords[0]+10*tile_coords[1]), tile_coords[0], tile_coords[1], height, size*(tile_coords[0]%2*2-1), size*(tile_coords[1]%2*2-1), 1)
                else:
                    draw_object_foreground(get_tex(decor, tile_coords[0]+10*tile_coords[1]), tile_coords[0], tile_coords[1], height, size*(tile_coords[0]%2*2-1), size*(tile_coords[1]%2*2-1), 1)
            else:
                height = OBJ[decor]["height"]
                if "flip" in OBJ[decor]["flags"]:
                    w,h = size*(int(index+tile_coords[0])%2*2-1), size*(int(index+tile_coords[1])%2*2-1)
                else:
                    w,h = size,size
                if "lightemit" in OBJ[decor].keys():
                    Renderer.light_list.append(geom_light(tile_coords[0], tile_coords[1], height, w,h, OBJ[decor]["lightemit"](curtime,tile_coords[0], tile_coords[1])))
                bot = decor
                if "bot" in OBJ[decor].keys():
                    bot = OBJ[decor]["bot"]
                if model == "singleshrub":
                    draw_object(get_tex(decor, index), tile_coords[0], tile_coords[1], height, w,h, 1)
                elif model == "doubleshrub":
                    draw_object(get_tex(bot, index), tile_coords[0], tile_coords[1], height/2, w,h, 1)
                    draw_object(get_tex(decor, index), tile_coords[0], tile_coords[1], height, -w,-h, 1)
                elif model == "singleobj":
                    draw_object(get_tex(decor, index), tile_coords[0], tile_coords[1], height, w,h, 0)
                elif model == "doubleobj":
                    draw_object(get_tex(bot, 0), tile_coords[0], tile_coords[1], 0, w,h, 0)
                    draw_object(get_tex(decor, 0), tile_coords[0], tile_coords[1], height, w,h, 0)
                elif model == "block":
                    wall = get_tex(decor, index)
                    draw_object(wall, tile_coords[0], tile_coords[1]-((y>window_size[1]//tile_size//2)-.5), height, 1, 0, 0)
                    draw_object(wall, tile_coords[0]-((x>window_size[0]//tile_size//2)-.5), tile_coords[1], height, 0, 1, 0)
                    draw_object(wall, tile_coords[0], tile_coords[1], height, 1, 1, 0)
                elif model == "roof":
                    draw_object(get_tex(decor, index), tile_coords[0], tile_coords[1], 1+height, 1, 1, 0)
        if len(tile_data) > 4:
            item = tile_data[3]
            if item != None and tile_data[4] > 0:
                w, h = (int(index + tile_coords[0]) % 2 * 2 - 1), (int(index + tile_coords[1]) % 2 * 2 - 1)
                draw_object(get_tex(item, index), tile_coords[0], tile_coords[1], height+0.02, w, h, 0)
        if tile_coords == selected_tile:
            draw_object(get_tex("selection", 0), selected_tile[0], selected_tile[1], 3+height, 1, 1, 0)
    char_speed = (sqrt(velocity[0]*velocity[0]+velocity[1]*velocity[1]))
    if (abs(velocity[0])+abs(velocity[1])) > 0.001 and curtime-steptime > 2/char_speed:
        steptime = curtime
        mat = player_tile_info[0]
        if mat == "water":
            seasplash_sfx.play()
        elif mat == "freshwater":
            fish_sfx.play()
        else:
            grass_step_sfx.play()
    char_anim += char_speed*20
    if char_speed < 0.001:
        char_anim = 0
    looking_direction = int(atan2((mouse_pos[0] - window_size[0] / 2), (mouse_pos[1] - window_size[1] / 2)) / tau * 8 + 4.5) % 8
    if looking_direction % 2:
        looking_direction = (looking_direction + 2) % 8

    if last_random_tick + 5.0 < time.time():
        # do random tick in 190x190 square around player (1 tick per tile per ingame day = 10 mins irl)
        for i in range(300):
            x, y = random.randint(-95, 95), random.randint(-95, 95)
            RT_coords = [ceil(screen_coords[0] / tile_size) + x - 1,
                           ceil(screen_coords[1] / tile_size) + y - 1]
            RT_data = get_tile_info(*RT_coords)
            if RT_data[1] in OBJ.keys():
                if "becomes" in OBJ[RT_data[1]].keys():
                    map.set_data(*RT_coords, (RT_data[0], OBJ[RT_data[1]]["becomes"], time.time()) + RT_data[3:])
                if "creates" in OBJ[RT_data[1]].keys():
                    if len(RT_data) < 4 or RT_data[3] == None or RT_data[4] == 0:
                        age = None if len(RT_data) < 3 else RT_data[2]
                        map.set_data(*RT_coords, (RT_data[0], RT_data[1], age) + (OBJ[RT_data[1]]["creates"][1], OBJ[RT_data[1]]["creates"][0]) + RT_data[5:])
        last_random_tick = time.time()
    if last_server_update+0.1 < time.time():
        if len(map.save_buffer) > 0:
            save_game()
        try:
            my_player_text = "player_update "+str(player_number)+','+str(pos[0])+','+str(pos[1])+','+str(char_direction)+','+str(looking_direction)+','+str(char_anim)+','+str(char_speed)
            sock.sendto(my_player_text.encode('utf-8'), server_address)
            data, address = sock.recvfrom(8192)
            data = data.decode('utf-8')
            data = data.split("&")
            world_text = pickle.loads(base64.b64decode(data[1][2:-1]))
            player_text = pickle.loads(base64.b64decode(data[0][2:-1]))
            for key in world_text.keys():
                map.apply_data(key[0], key[1], world_text[key])
            server_fails = 0
        except BlockingIOError:
            server_fails += 1
            if server_fails > 60:
                menu = 1
                text.append("Error reaching server", "progress will not be saved")
                construct_overlay()
                server_fails = 0
        last_server_update = time.time()

    for number in player_text.keys():
        if int(number) != player_number:
            values = player_text[number]
            coords = [float(values[0])-.5, float(values[1])-.5]
            direc = int(values[2])
            look = int(values[3])
            anim = float(values[4])
            speed = float(values[5])
            dt = 1000*(time.time()-last_server_update)
            anim += dt/20 * speed*20
            if direc%2:
                dx, dy = dt*speed*cos(-direc*tau/8), dt*speed*sin(-direc*tau/8)
            else:
                dx, dy = dt*speed*cos(direc*tau/8+tau/4), dt*speed*sin(direc*tau/8-tau/4)
            draw_object(get_tex("charlegs"+str(direc), anim), coords[0]+dx, coords[1]+dy, 0.05, 2, 2, 1)
            draw_object(get_tex("charhands"+str(direc), anim), coords[0]+dx, coords[1]+dy, 0.07, 2, 2, 1)
            draw_object(get_tex("charhead"+str(look), number), coords[0]+dx, coords[1]+dy, 0.08, 2, 2, 1)
    # add player textures to vertex list
    mat = player_tile_info[0]
    if mat != "water":
        Renderer.vert_list.append(screen_transform(window_size[0] / 2 - tile_size, window_size[1] / 2 - tile_size, 0.05, 2 * tile_size, 2 * tile_size, get_tex("charlegs"+str(char_direction),char_anim), 0))
    Renderer.vert_list.append(screen_transform(window_size[0] / 2 - tile_size, window_size[1] / 2 - tile_size, 0.07, 2 * tile_size, 2 * tile_size, get_tex("charhands"+str(char_direction),char_anim), 0))
    Renderer.vert_list.append(screen_transform(window_size[0] / 2 - tile_size, window_size[1] / 2 - tile_size, 0.08, 2 * tile_size, 2 * tile_size, get_tex("charhead"+str(looking_direction),player_number), 0))
    item = hotbar[int(selected_item_slot)]
    if item[2] > 0 and item[0] in OBJ.keys() and "lightemit" in OBJ[item[0]].keys():
        Renderer.light_list.append(((0, 0, 1), OBJ[item[0]]["lightemit"](curtime, 1, 1)))
    draw_object(get_tex("selectionbot",0), selected_tile[0], selected_tile[1], 3, 1, 1, 0)
    for c in range(10):
        draw_shadow(get_tex("cloud", c),
                    screen_coords[0] / tile_size + (time.time()*2+5647*c-screen_coords[0] / tile_size)%(400+c)-100,
                    screen_coords[1] / tile_size + (time.time()/5+4674*c-screen_coords[1] / tile_size)%(300+c)-100,
                    1,
                    100*(int(c)%2*2-1),
                    100*(int(c//2)%2*2-1), 2)
    for c in range(5):
        draw_weather(get_tex("cloud", c),
                     screen_coords[0] / tile_size + (time.time()/10+48634*c-screen_coords[0] / tile_size)%(400+c)-100,
                     screen_coords[1] / tile_size + (time.time()/40+87356*c-screen_coords[1] / tile_size)%(300+c)-100,
                     1,
                     100*(int(c)%2*2-1),
                     100*(int(c//2)%2*2-1), 2)
    r = min(max(sin((time.time() * tau) / 60 / 10) + 1.32, 0), 1)**4
    if r >= 0.03:
        Renderer.reflection_list.append((0, 0, 0, 2, 2, get_tex("sky", 0), 0))
    else:
        Renderer.reflection_list.append((0, 0, 0, 2, 2, get_tex("moon", 0), 0))

    Renderer.render((mouse_pos[0]/window_size[0]*2-1, 1-mouse_pos[1]/window_size[1]*2), tile_size)
    if "press"+str(pygame.K_F2) in keydown_set:
        try: os.mkdir("screenshots")
        except: pass
        file_name = os.path.join("screenshots", "screenshot"+str(int(time.time()))+".png")
        file = open(file_name, "wb")
        pygame.image.save(pygame.transform.flip(pygame.image.fromstring(Renderer.ctx.screen.read(Renderer.ctx.screen.viewport), Renderer.ctx.screen.viewport[2:], "RGB"), False, True), file, "PNG")
        file.close()
        keydown_set.remove("press"+str(pygame.K_F2))
    pygame.display.flip()
    clock.tick(FPS)

i = 60
while i>0 and running:
    i-=1
    main()
cProfile.run('main()', sort=2)
while running:
    main()
