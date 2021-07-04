from mcdreforged.api.all import *
import os
import json
import time
import random
import copy

PLUGIN_METADATA = {
    'id': 'changebattle',
    'version': '1.0.0',
    'name': 'Change Battle',
    'description': '一个PVP小游戏，定时互换位置',
    'author': [
        'DancingSnow'
    ],
    'dependencies': {
        'minecraft_data_api': '*',
        'more_apis': '*',
        'mcdreforged': '>=1.0.0'
    },
    'link': 'https://github.com/DancingSnow0517/ChangeBattle'
}

dim_convert = {
    -1: 'minecraft:the_nether',
    0: 'minecraft:overworld',
    1: 'minecraft:the_end'
}

prefix = '!!CB'
ConfigFile = 'config/ChangeBattle.json'
cfg = {}
confirm_statu = False

game_status = False
now_round = 0
playerList = []
Last_info = []
after = []
'''
!!CB 显示本消息 --
!!CB start 开始游戏 -- 
!!CB options 显示可选选项 
!!CB status 显示游戏状态 --
!!CB stop 强制停止当前游戏 --
!!CB set [选项]来设置各种选项 
!!CB reload 重载配置文件 --
!!CB team 队伍模式 ++
'''

default_config = {
    "Center": [0, 0],
    "Size": 2000,
    "NextSize": [0.55, 0.7],
    "Time": 300,
    "NextTime": 0.7,
    "SaveTime": 0.6,
    "rounds": 7,
    "RandomCenter": False,
    "minimum_permission_level": {
        'start': 0,
        'status': 0,
        'stop': 3,
        'set': 2,
        'reload': 2
    }
}


def game_stoped(server: ServerInterface):
    server.execute('scoreboard objectives remove INFO')
    server.execute('bossbar remove minecraft:battle')
    server.execute(f'execute in minecraft:overworld run worldborder set 1000000 0')
    server.execute(f'execute in minecraft:the_nether run worldborder set 1000000 0')


def infoUpdata(server, game_time, center, rounds, left_time, left_players, size):
    global Last_info
    """
    ======INFO======
    游戏已运行{game_time}秒
    当前世界中心{center[0]},[center[1]]
    边界大小
    目前是第{rounds}回合
    距离下次交换还有{left_time}秒
    还有{left_players}名玩家存活
    """
    for i in range(6):
        if i == 5:
            INFO = f'当前世界中心§b{center[0]}§r，§b{center[1]}'
            if Last_info[i] != INFO:
                server.execute(f'scoreboard players reset {Last_info[i]}')
            server.execute(f'scoreboard players set {INFO} INFO {i}')
            Last_info[i] = INFO
        elif i == 4:
            INFO = f'当前边界大小§b{size}§r格'
            if Last_info[i] != INFO:
                server.execute(f'scoreboard players reset {Last_info[i]}')
            server.execute(f'scoreboard players set {INFO} INFO {i}')
            Last_info[i] = INFO
        elif i == 3:
            INFO = f'距离下次交换还有§b{left_time}§r秒'
            if Last_info[i] != INFO:
                server.execute(f'scoreboard players reset {Last_info[i]}')
            server.execute(f'scoreboard players set {INFO} INFO {i}')
            Last_info[i] = INFO
        elif i == 2:
            INFO = f'目前是第§b{rounds}§r回合'
            if Last_info[i] != INFO:
                server.execute(f'scoreboard players reset {Last_info[i]}')
            server.execute(f'scoreboard players set {INFO} INFO {i}')
            Last_info[i] = INFO
        elif i == 1:
            INFO = f'游戏已运行§b{int(game_time)}§r秒'
            if Last_info[i] != INFO:
                server.execute(f'scoreboard players reset {Last_info[i]}')
            server.execute(f'scoreboard players set {INFO} INFO {i}')
            Last_info[i] = INFO
        elif i == 0:
            INFO = f'还有§b{left_players}§r名玩家存活'
            if Last_info[i] != INFO:
                server.execute(f'scoreboard players reset {Last_info[i]}')
            server.execute(f'scoreboard players set {INFO} INFO {i}')
            Last_info[i] = INFO


def player_rand(array):
    rand = copy.copy(array)
    if len(array) == 1:
        return array
    elif len(array) == 2:
        rand = [array[1], array[0]]
        return rand
    random.seed(time.time())
    random.shuffle(rand)
    for i in range(len(array)):
        if rand[i] == array[i]:
            return player_rand(array)
    return rand


def change(server):
    global after
    pos = {}
    api = server.get_plugin_instance('minecraft_data_api')
    for i in playerList:
        pos[i] = {}
        pos[i]["pos"] = api.get_player_coordinate(i)
        pos[i]["dim"] = api.get_player_dimension(i)
    after = player_rand(playerList)
    for i in range(len(playerList)):
        server.execute(
            f'execute in {dim_convert[pos[after[i]]["dim"]]} run tp {playerList[i]} {pos[after[i]]["pos"][0]} {pos[after[i]]["pos"][1]} {pos[after[i]]["pos"][2]}')


def BossBar(server: ServerInterface, Left_time, Max_time, text, color):
    raw = {
        "text": text.format(Left_time),
        "color": color
    }
    server.execute(f'bossbar set minecraft:battle color {color}')
    server.execute(f'bossbar set minecraft:battle max {Max_time}')
    server.execute(f'bossbar set minecraft:battle name {json.dumps(raw)}')
    server.execute(f'bossbar set minecraft:battle value {Left_time}')


@new_thread('ChangeBattle')
def main(server: ServerInterface):
    global game_status
    global now_round
    global Last_info
    # 玩家初始化
    server.execute('clear @a')
    server.execute(
        'give @a minecraft:stone_sword{Enchantments:[{id:"minecraft:unbreaking",lvl:1}]} 1')
    server.execute(
        'give @a minecraft:stone_pickaxe{Enchantments:[{id:"minecraft:efficiency",lvl:2},{id:"minecraft:unbreaking",lvl:1}]} 1')
    server.execute(
        'give @a minecraft:stone_axe{Enchantments:[{id:"minecraft:efficiency",lvl:2},{id:"minecraft:unbreaking",lvl:1}]} 1')
    server.execute(
        'give @a minecraft:stone_shovel{Enchantments:[{id:"minecraft:efficiency",lvl:2},{id:"minecraft:unbreaking",lvl:1}]} 1')
    server.execute('effect give @a minecraft:saturation 1 255')
    server.execute('effect give @a minecraft:regeneration 1 255')
    server.execute('gamemode survival @a')

    server.execute('bossbar remove minecraft:battle')
    server.execute('bossbar add battle {"text":"ChangeBattle"}')
    server.execute('bossbar set minecraft:battle players @a')

    server.execute('scoreboard objectives remove INFO')
    server.execute('scoreboard objectives add INFO dummy {"text":"========INFO========","color":"light_purple"}')
    server.execute('scoreboard objectives setdisplay sidebar INFO')

    # 世界初始化
    if cfg["RandomCenter"]:
        x = random.randint(-100000, 100000)
        z = random.randint(-100000, 100000)
    else:
        x = cfg["Center"][0]
        z = cfg["Center"][1]
    server.execute(f'execute in minecraft:overworld run worldborder center {x} {z}')
    server.execute(f'execute in minecraft:the_nether run worldborder center {x} {z}')
    server.execute('execute in minecraft:overworld as @a run tp 0 100 0')
    server.execute(f'spreadplayers {x} {z} {cfg["Size"] * 0.25} {cfg["Size"] * 0.45} false @a')

    server.execute(f'scoreboard players set centerX vars {x}')
    server.execute(f'scoreboard players set centerZ vars {z}')

    now_size = cfg["Size"]
    now_time = cfg["Time"]
    now_round = 1
    t = now_time
    game_start_time = time.time()
    server.execute(f'execute in minecraft:overworld run worldborder set {now_size} 0')
    server.execute(f'execute in minecraft:the_nether run worldborder set {now_size} 0')
    n_min = int(now_size * cfg["NextSize"][0])
    n_max = int(now_size * cfg["NextSize"][1])
    next_size = random.randint(n_min, n_max)
    Last_info = [0, 1, 2, 3, 4, 5]
    while game_status:
        time.sleep(1)
        if now_size <= 128:
            server.execute('effect give @a minecraft:glowing 20')
            continue
        t -= 1
        infoUpdata(server, time.time() - game_start_time, [x, z], now_round, t, len(playerList), now_size)
        if t in range(int(now_time * (1 - cfg["SaveTime"])), now_time):
            BossBar(server, t - int(now_time * (1 - cfg["SaveTime"])), int(now_time * cfg["SaveTime"]), '{} 秒后缩圈',
                    'green')
        elif t in range(6, int(now_time * (1 - cfg["SaveTime"]))):
            if t == (int(now_time * (1 - cfg["SaveTime"])) - 1):
                server.execute(
                    f'execute in minecraft:overworld run worldborder set {next_size} {now_time - int(now_time * cfg["SaveTime"])}')
                server.execute(
                    f'execute in minecraft:the_nether run worldborder set {int(next_size / 8)} {now_time - int(now_time * cfg["SaveTime"])}')
            BossBar(server, t, int(now_time * cfg["SaveTime"]), '{} 秒后进行交换', 'red')
        elif t in range(1, 6):
            cb_tell(server, '还有 {} 秒互换')
            BossBar(server, t, int(now_time * cfg["SaveTime"]), '{} 秒后进行交换', 'red')
            server.execute('execute at @a run playsound minecraft:entity.arrow.hit_player player @p ~ ~ ~ 1 0.5')
        elif t == 0:
            cb_tell(server, '正在互换！')
            BossBar(server, t, int(now_time * cfg["SaveTime"]), '{} 秒后进行交换', 'red')
            server.execute('execute at @a run playsound minecraft:entity.arrow.hit_player player @p ~ ~ ~ 1 1')
            change(server)
            now_round += 1
            now_size = next_size
            n_min = int(now_size * cfg["NextSize"][0])
            n_max = int(now_size * cfg["NextSize"][1])
            next_size = random.randint(n_min, n_max)
            now_time = int(now_time * cfg["NextTime"])
            t = now_time


def cb_tell(server: ServerInterface, msg):
    server.say(f'§d[{PLUGIN_METADATA.get("name")}]§r{msg}')


def death_message(server: ServerInterface, message):
    global playerList
    global game_status
    player = message.split(' ')[0]
    if game_status:
        if player in playerList:
            cb_tell(server, f'玩家 {player} 出局')
            playerList.remove(player)
            server.execute(f'gamemode spectator {player}')
        if len(playerList) <= 1:
            cb_tell(server, '游戏结束')
            cb_tell(server, f'玩家 {playerList[0]} 获得胜利')
            game_status = False
            game_stoped(server)


def config(mode, js=None):
    if mode == 'r':
        if not os.path.exists(ConfigFile):
            with open(ConfigFile, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
                return default_config
        else:
            with open(ConfigFile, 'r', encoding='utf-8') as f:
                return json.load(f)
    elif mode == 'w' and js is not None:
        with open(ConfigFile, 'w', encoding='utf-8') as f:
            json.dump(js, f, indent=4)


def status(Source: CommandSource):
    server = Source.get_server()
    if not game_status:
        cb_tell(server, '游戏未运行')
        return
    alive = ''
    for i in playerList:
        alive += f'{i}, '
    cb_tell(server, '=====Change Battle status=====')
    server.say(alive)
    server.say(f'共 {len(playerList)} 人存活')
    server.say(f'目前是第 {now_round} 个圈')


def print_help_msg(Source: CommandSource):
    Source.reply(
        RText('Test').set_color(RColor.aqua).set_hover_text('单击执行').set_click_event(RAction.run_command, '!!CB'))


@new_thread('ChangeBattle')
def start(Source: CommandSource):
    global playerList
    global confirm_statu
    server = Source.get_server()
    if game_status:
        cb_tell(server, RText('游戏已经开始！').set_color(RColor.red))
        return
    if server.is_server_startup():
        cb_tell(server, '准备开始游戏')
        api = server.get_plugin_instance('minecraft_data_api')
        amount, limit, playerList = api.get_server_player_list()
        if amount <= 1:
            cb_tell(server, '人数不足，无法开始！')
            return
        string = ''
        for i in playerList:
            string += f'{i}, '
        string = string.rstrip(', ')
        string += f'\n共 {amount} 名玩家\n!!CB start confirm 以确认\n!!CB start abort 以取消'
        server.say(string)
        confirm_statu = True


def stop(Source: CommandSource):
    global game_status
    server = Source.get_server()
    if game_status:
        cb_tell(server, '游戏已强制停止')
        game_status = False
        game_stoped(server)
    else:
        cb_tell(server, '游戏没有在运行')


def confirm(Source: CommandSource):
    global confirm_statu
    global game_status
    server = Source.get_server()
    if confirm_statu:
        cb_tell(server, '3')
        time.sleep(1)
        cb_tell(server, '2')
        time.sleep(1)
        cb_tell(server, '1')
        time.sleep(1)
        cb_tell(server, '游戏开始')
        game_status = True
        main(server)
        confirm_statu = False
        game_stoped(server)
    else:
        cb_tell(server, '游戏还未准备')


def abort(Source: CommandSource):
    global confirm_statu
    server = Source.get_server()
    if confirm_statu:
        cb_tell(server, '游戏已取消准备')
        confirm_statu = False
    else:
        cb_tell(server, '游戏还未准备')


def reload(Source: CommandSource):
    global cfg
    cfg = config('r')
    cb_tell(Source.get_server(), '配置文件重载成功')


def options(Source: CommandSource):
    """
    当前中心为 {} {} [✎]
    当前大小为 {} [✎]
    下一轮时间为 {} [✎]
    下一轮大小范围 {} {} [✎]
    当前为 {}
    下一轮时间 {} [✎]
    安全时间 {} [✎]
    随机中心 [ON] [OFF]
    """
    player = Source.player
    server = Source.get_server()
    # 设置中心
    text = [
        {
            "text": f"当前中心为 §bX:{cfg['Center'][0]}, Z:{cfg['Center'][1]} §r"
        },
        {
            "text": "[✎]",
            "clickEvent": {
                "action": "suggest_command",
                "value": f"{prefix} set Center <X> <Z>"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击修改"
            },
            "color": "green"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    # 设置大小
    text = [
        {
            "text": f"当前边界大小为 §b{cfg['Size']}§r 格 "
        },
        {
            "text": "[✎] ",
            "clickEvent": {
                "action": "suggest_command",
                "value": f"{prefix} set Size <size>"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击修改"
            },
            "color": "green"
        },
        {
            "text": "[1000] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Size 1000"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将大小设置为 1000"
            },
            "color": "yellow"
        },
        {
            "text": "[2000] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Size 2000"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将大小设置为 2000"
            },
            "color": "yellow"
        },
        {
            "text": "[3000] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Size 3000"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将大小设置为 3000"
            },
            "color": "yellow"
        },
        {
            "text": "[5000] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Size 5000"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将大小设置为 5000"
            },
            "color": "yellow"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    # 设置下一个圈大小
    text = [
        {
            "text": f"当前下个边界大小 §b[{cfg['NextSize'][0]} - {cfg['NextSize'][1]}]§r "
        },
        {
            "text": "[✎]",
            "clickEvent": {
                "action": "suggest_command",
                "value": f"{prefix} set NextSize <min> <max>"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击修改"
            },
            "color": "green"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    text = [
        {
            "text": "Tips: “min”和“max”中填写0-1的小数，1代表大小不会变化",
            "color": "dark_red"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    # 设置时间
    text = [
        {
            "text": f"当前时间为 §b{cfg['Time']}§r 秒 "
        },
        {
            "text": "[✎] ",
            "clickEvent": {
                "action": "suggest_command",
                "value": f"{prefix} set Time <time>"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击修改"
            },
            "color": "green"
        },
        {
            "text": "[300] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Time 300"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将时间设置为 300"
            },
            "color": "yellow"
        },
        {
            "text": "[600] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Time 600"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将时间设置为 600"
            },
            "color": "yellow"
        },
        {
            "text": "[1200] ",
            "clickEvent": {
                "action": "run_command",
                "value": f"{prefix} set Time 1200"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击将时间设置为 1200"
            },
            "color": "yellow"
        },
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    # 设置下一轮时间
    text = [
        {
            "text": f"下一轮时间为 §b[{cfg['NextTime']}]§r "
        },
        {
            "text": "[✎]",
            "clickEvent": {
                "action": "suggest_command",
                "value": f"{prefix} set NextTime <NextTime>"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击修改"
            },
            "color": "green"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    text = [
        {
            "text": "Tips: “NextTime”中填写0-1的小数，1代表时间不会变化",
            "color": "dark_red"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    # 设置安全时间
    text = [
        {
            "text": f"当前安全时间 §b[{cfg['SaveTime']}]§r "
        },
        {
            "text": "[✎]",
            "clickEvent": {
                "action": "suggest_command",
                "value": f"{prefix} set SaveTime <SaveTime>"
            },
            "hoverEvent": {
                "action": "show_text",
                "value": "单击修改"
            },
            "color": "green"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    text = [
        {
            "text": "Tips: “SaveTime”中填写0-1的小数，1代表全是安全时间，缩圈会瞬间进行",
            "color": "dark_red"
        }
    ]
    server.execute(f'tellraw {player} {json.dumps(text)}')
    # 随机中心
    if cfg["RandomCenter"]:
        text = [
            {
                "text": "随机中心开关 "
            },
            {
                "text": "[ON] ",
                "hoverEvent": {
                    "action": "show_text",
                    "value": "已开启"
                },
                "color": "gray"
            },
            {
                "text": "[OFF]",
                "clickEvent": {
                    "action": "run_command",
                    "value": f"{prefix} set RandomCenter False"
                },
                "hoverEvent": {
                    "action": "show_text",
                    "value": "单击修改"
                },
                "color": "green"
            }
        ]
    else:
        text = [
            {
                "text": "随机中心开关 "
            },
            {
                "text": "[ON] ",
                "clickEvent": {
                    "action": "run_command",
                    "value": f"{prefix} set RandomCenter True"
                },
                "hoverEvent": {
                    "action": "show_text",
                    "value": "单击修改"
                },
                "color": "red"
            },
            {
                "text": "[OFF]",
                "hoverEvent": {
                    "action": "show_text",
                    "value": "已关闭"
                },
                "color": "gray"
            }
        ]
    server.execute(f'tellraw {player} {json.dumps(text)}')


def setCenter(Source: CommandSource, msg):
    global cfg
    cfg["Center"][0] = msg["centerX"]
    cfg["Center"][1] = msg["centerZ"]
    config('w', cfg)
    Source.reply(f'中心点已设置为 §bX:{cfg["Center"][0]}, Z:{cfg["Center"][1]}')


def setSize(Source: CommandSource, msg):
    global cfg
    cfg["Size"] = msg["Size"]
    config('w', cfg)
    Source.reply(f'边界大小已设置为 §b{cfg["Size"]}')


def setNextSize(Source: CommandSource, msg):
    global cfg
    if msg['Next_min'] <= msg['Next_max']:
        cfg["NextSize"][0] = msg['Next_min']
        cfg["NextSize"][1] = msg['Next_max']
        config('w', cfg)
        Source.reply(f'边界大小已设置为 §b[{cfg["NextSize"][0]} - {cfg["NextSize"][1]}]')
    else:
        Source.reply(f'§c{msg["Next_min"]} 应小于 {msg["Next_max"]}')


def setTime(Source: CommandSource, msg):
    global cfg
    cfg["Time"] = msg["Time"]
    config('w', cfg)
    Source.reply(f'时间已设置为 §b{cfg["Time"]}')


def setNextTime(Source: CommandSource, msg):
    global cfg
    cfg["NextTime"] = msg["NextTime"]
    config('w', cfg)
    Source.reply(f'下一轮时间已设置为 §b[{cfg["NextTime"]}]')


def setSaveTime(Source: CommandSource, msg):
    global cfg
    cfg["SaveTime"] = msg["SaveTime"]
    config('w', cfg)
    Source.reply(f'安全时间已设置为 §b[{cfg["NextTime"]}]')


def setRandomCenter(Source: CommandSource, msg):
    global cfg
    if msg["RandomCenter"] == 'True':
        cfg["RandomCenter"] = True
        config('w', cfg)
        Source.reply('随机中心已开启')
    elif msg["RandomCenter"] == 'False':
        cfg["RandomCenter"] = False
        config('w', cfg)
        Source.reply('随机中心已关闭')
    else:
        Source.reply('§c值必须为“True”或“False”')


def register_command(server: ServerInterface):
    def get_literal_node(literal):
        lvl = cfg['minimum_permission_level'].get(literal, 0)
        return Literal(literal).requires(lambda src: src.has_permission(lvl), lambda: '权限不足')

    server.register_command(
        Literal(prefix).runs(print_help_msg).
            then(get_literal_node('start').runs(start).
                 then(Literal('confirm').runs(confirm)).
                 then(Literal('abort').runs(abort))).
            then(get_literal_node('reload').runs(reload)).
            then(get_literal_node('stop').runs(stop)).
            then(get_literal_node('status').runs(status)).
            then(get_literal_node('set').runs(options).
                 then(Literal('Center').
                      then(Integer('centerX').
                           then(Integer('centerZ').runs(setCenter)))).
                 then(Literal('Size').
                      then(Integer('Size').runs(setSize))).
                 then(Literal('NextSize').
                      then(Float('Next_min').at_max(1).at_min(0).
                           then(Float('Next_max').at_max(1).at_min(0).runs(setNextSize)))).
                 then(Literal('Time').
                      then(Integer('Time').at_min(0).runs(setTime))).
                 then(Literal('NextTime').
                      then(Float('NextTime').at_min(0).at_max(1).runs(setNextTime))).
                 then(Literal('SaveTime').
                      then(Float('SaveTime').at_min(0).at_max(1).runs(setSaveTime))).
                 then(Literal('RandomCenter').
                      then(Text('RandomCenter').runs(setRandomCenter)))))


def on_load(server: ServerInterface, old):
    global cfg
    cfg = config('r')
    server.register_help_message(prefix, 'Change Battle 帮助')
    server.register_event_listener('more_apis.death_message', death_message)
    register_command(server)
    server.execute('team add ChangeBattle')
    server.execute('team modify ChangeBattle color gold')
    server.execute('team modify ChangeBattle nametagVisibility never')


def on_player_joined(server: ServerInterface, player: str, info: Info):
    server.execute(f'team join ChangeBattle {player}')

