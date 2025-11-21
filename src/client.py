#!/usr/bin/env python3

import discord
from discord.ext import commands
from discord.ui import Button, View
import re
from db import db
import json
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("TOKEN")

# プロジェクトの `src` ディレクトリを基準にファイルを扱う
base_dir = Path(__file__).resolve().parent

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix="!", intents=intents)

class MyView(View):
    def __init__(self, list):
        super().__init__()
        for obj in list:
            print(obj)
            custom_emoji = r'<:[a-zA-Z0-9_]+:[0-9]+>'
            
            if re.fullmatch(custom_emoji, obj[1]) == None:
                self.add_item(Button(label=obj[1], style=discord.ButtonStyle.secondary, custom_id=str(obj[0])))
            else:
                self.add_item(Button(emoji=obj[1], style=discord.ButtonStyle.secondary, custom_id=str(obj[0])))


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    #database = db()
    #database.create_table()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    custom_id = interaction.data['custom_id']
    DB = db()
    data = DB.get_record_by_id(custom_id)[0]
    await play_audio(interaction, data[2])

@bot.command()
async def list(ctx):
    DB = db()
    all_record = DB.get_all_record()
    blocks = chunk_list(all_record, 25)
    for block in blocks:
        view = MyView(block)
        await ctx.send(view=view)

def chunk_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
    
async def play_audio(interaction: discord.Interaction, audio_file: str):
    await interaction.response.defer()
    # ユーザーが音声チャネルに接続しているか確認
    if interaction.user.voice is None:
        await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
        return

    # ボットがすでに接続している場合、音声チャネルに再接続しないようにします
    voice_channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    # 音声ファイルを再生
    if voice_client.is_playing():
        voice_client.stop()
    
    source = discord.FFmpegPCMAudio(str(base_dir / 'audio_files' / audio_file))
    voice_client.play(source)

@bot.listen()
async def on_message(message):

    if message.content.startswith('!regist'):
        extensions = ['wav', 'mp3']
        extensions = tuple(extensions)
        custom_emoji = r'<:[a-zA-Z0-9_]+:[0-9]+>'
        args = message.content.split(' ')

        if len(args) != 2:
            await message.channel.send('引数が不正です')
            return
        if str(message.attachments) == '[]':
            await message.channel.send('ファイルが添付されていません')
            return
        
        custom_emoji2 = re.fullmatch(custom_emoji, args[1])
        split_v1 = str(message.attachments).split("filename='")[1]
        filename = str(split_v1).split("' ")[0]
        DB = db()
        duplication = DB.get_record_by_name(args[1])

        if custom_emoji2 == None and len(args[1]) > 5:
            await message.channel.send('登録名称が長すぎます')
            return

        if len(duplication) != 0:
            await message.channel.send('すでにこの絵文字は登録されています')
            return
        elif not filename.endswith(extensions):
            await message.channel.send('ファイルの拡張子が不正です')
            return
        else:
            # 添付ファイルをプロジェクト内の audio_files に保存
            await message.attachments[0].save(fp=str(base_dir / 'audio_files' / filename))
            audio_register(args[1], filename)
            await message.channel.send('登録が完了しました:' + args[1] + ' ' + filename)
    elif message.content.startswith('!rm'):
        args = message.content.split(' ')
        if len(args) != 2:
            await message.channel.send('引数が不正です')
            return
        else:
            DB = db()
            record = DB.get_record_by_name(args[1])
            if len(record) == 0:
                await message.channel.send('その名前の登録はありません')
                return
            else:
                file_path = Path(base_dir / 'audio_files' / record[0][2])
                if file_path.exists():
                    file_path.unlink()
                    DB.delete_record_by_id(record[0][0])
                    await message.channel.send('削除が完了しました:' + args[1])
                else:
                    await message.channel.send('ファイルが見つかりません')

def audio_register(name, filepath):
    DB = db()
    DB.insert_record(name, filepath)


bot.run(api_key)