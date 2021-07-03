from mcdreforged.api.all import *
import os
import json
import time
import random

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
        'more_apis': '*'
    },
    'link': 'https://github.com/DancingSnow0517/ChangeBattle'
}

prefix = '!!CB'
ConfigFile = 'config/ChangeBattle.json'
cfg = {}
confirm_statu = False

game_status = False
playerList = []
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
    "time": 600,
    "NextTime": 0.7,
    "SaveTime": 0.6,
    "rounds": 7,
    "RandomCenter": False,
    "minimum_permission_level": {
        'start': 0,
        'options': 2,
        'status': 0,
        'stop': 3,
        'set': 2,
        'reload': 2
    }
}


def infoUpdata(server):
    pass


def change(server):
    pass


@new_thread('ChangeBattle')
def main(server: ServerInterface):
    global game_status
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

    # 世界初始化
    if cfg["RandomCenter"]:
        x = random.randint(-100000, 100000)
        z = random.randint(-100000, 100000)
    else:
        x = cfg["Center"][0]
        z = cfg["Center"][1]
    server.execute(f'worldborder center {x} {z}')
    server.execute(f'spreadplayers {x} {z} {cfg["Size"] * 0.25} {cfg["Size"] * 0.45} false @a')

    now_size = cfg["Size"]
    now_time = cfg["time"]
    now_round = 1
    t = now_time
    server.execute(f'worldborder set {now_size} 0')
    while game_status:
        time.sleep(1)
        t -= 1
        if t in range(now_time*cfg["SaveTime"], now_time):
            infoUpdata(server)
        elif t in range(6, now_time*cfg["SaveTime"]):
            infoUpdata(server)
        elif t in range(1, 6):
            cb_tell(server, '还有 {} 秒互换')
            server.execute('execute at @a run playsound minecraft:entity.arrow.hit_player player @p ~ ~ ~ 1 0.5')
        elif t == 0:
            cb_tell(server, '正在互换！')
            server.execute('execute at @a run playsound minecraft:entity.arrow.hit_player player @p ~ ~ ~ 1 1')
            change(server)

            now_round += 1

            n_min = int(now_size * cfg["NextSize"][0])
            n_max = int(now_size * cfg["NextSize"][1])
            now_size = random.randint(n_min, n_max)

            now_time = int(now_time * cfg["NextTime"])
            t = now_time


def cb_tell(server: ServerInterface, msg):
    server.say(f'§d[{PLUGIN_METADATA.get("name")}]§r{msg}')


def death_message(server: ServerInterface, death_message):
    server.say(death_message)


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
            then(get_literal_node('status').runs(status)))


def on_load(server: ServerInterface, old):
    global cfg
    cfg = config('r')
    server.register_help_message(prefix, 'Change Battle 帮助')
    server.register_event_listener('more_apis.death_message', death_message)
    register_command(server)
