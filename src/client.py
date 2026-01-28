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
import yt_dlp
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if gemini_api_key:
    gemini_client = genai.Client(api_key=gemini_api_key)
else:
    gemini_client = None
    print("Warning: GEMINI_API_KEY is not set.")

# プロジェクトの `src` ディレクトリを基準にファイルを扱う
base_dir = Path(__file__).resolve().parent

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

class MyView(View):
    def __init__(self, list):
        super().__init__()
        for obj in list:
            # obj[1]がint型の場合エラーになるので対策
            obj = obj[0], str(obj[1]), obj[2]
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
    guild_id = str(interaction.guild_id)
    DB = db()
    data = DB.get_record_by_id(custom_id)[0]
    await play_audio(interaction, data[2], guild_id)

@bot.command()
async def list(ctx):
    guild_id = str(ctx.guild.id)
    DB = db()
    all_record = DB.get_all_record()
    filter_record = [t for t in all_record if str(t[3]) == guild_id]
    blocks = chunk_list(filter_record, 25)
    for block in blocks:
        view = MyView(block)
        await ctx.send(view=view)

def chunk_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
    
async def play_audio(interaction: discord.Interaction, audio_file: str, guild_id: str):
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
    
    source = discord.FFmpegPCMAudio(f"{base_dir}/audio_files/{guild_id}/{audio_file}")
    voice_client.play(source)

@bot.listen()
async def on_message(message):
    if message.author.bot:
        return
        
    guild_id = str(message.guild.id)

    if bot.user in message.mentions and gemini_client:
        async with message.channel.typing():
            try:
                # メンションを削除してコンテンツを取得
                prompt = message.content.replace(f'<@{bot.user.id}>', '').strip()
                if not prompt:
                    prompt = "こんにちは" # デフォルトメッセージ

                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="必ず淫夢語録で回答してください"
                    )
                )
                response_text = response.text
                # Discordの文字数制限（2000文字）に対応するため分割して送信
                if len(response_text) > 2000:
                    for i in range(0, len(response_text), 2000):
                        chunk = response_text[i:i+2000]
                        await message.reply(chunk)
                else:
                    await message.reply(response_text)
            except Exception as e:
                print(f"Gemini API Error: {e}")
                await message.channel.send("申し訳ありません。エラーが発生しました。")
        return

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
        all_record = DB.get_record_by_name(args[1])
        duplication = [t for t in all_record if str(t[3]) == guild_id]

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
            # フォルダが無ければ作成
            dir = f"{base_dir}/audio_files/{guild_id}"
            Path(dir).mkdir(parents=True, exist_ok=True)

            # 添付ファイルをプロジェクト内の audio_files に保存
            await message.attachments[0].save(fp=f"{dir}/{filename}")
            audio_register(args[1], filename, guild_id)
            await message.channel.send('登録が完了しました:' + args[1] + ' ' + filename)
    elif message.content.startswith('!remove'):
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
                file_path = Path(f"{base_dir}/audio_files/{record[0][3]}/{record[0][2]}")
                if file_path.exists():
                    file_path.unlink()
                    DB.delete_record_by_id(record[0][0])
                    await message.channel.send('削除が完了しました:' + args[1])
                else:
                    await message.channel.send('ファイルが見つかりません')
    elif message.content.startswith('!yarimasune'):
        await message.channel.send('やりますねぇ！')

def audio_register(name, filepath, guild_id):
    DB = db()
    DB.insert_record(name, filepath, guild_id)


@bot.command()
async def play(ctx, url):
    # VCに未接続なら接続
    if ctx.author.voice is None:
        return await ctx.send("ボイスチャンネルに入ってください")

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client

    # すでに再生中なら停止
    if vc.is_playing():
        vc.stop()

    # YouTube / ニコニコ動画 → 音源URL を取得
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info["url"]
    except Exception as e:
        return await ctx.send(f"❌ 動画の取得に失敗しました: {e}")

    source = discord.FFmpegPCMAudio(
        audio_url,
        before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        options='-vn'
    )

    # サービス名を取得（YouTube, niconico など）
    extractor = info.get('extractor', '').replace(':', ' ').title()
    title = info.get('title', '不明')

    vc.play(source)
    await ctx.send(f"▶ 再生開始 [{extractor}]: {title}")


@bot.event
async def on_voice_state_update(member, before, after):
    # ボイスチャンネルから離脱したイベントだけを見る
    if before.channel is not None and (after.channel != before.channel):
        channel = before.channel

        # このチャンネルに bot がいるか？
        if channel.guild.voice_client is None:
            return

        bot_voice = channel.guild.voice_client

        # Bot が現在いるチャンネルと一致しているか？
        if bot_voice.channel != channel:
            return

        # 残っているメンバーに人間がいるかチェック
        humans = [m for m in channel.members if not m.bot]

        if len(humans) == 0:
            await bot_voice.disconnect()
            print("🔊 誰もいなくなったので BOT は退出しました。")


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📘 Help",
        description="使用できるコマンド一覧です。",
        color=discord.Color.blue()
    )

    embed.add_field(name="!regist <NAME>", value="ファイルを添付して音声を登録します", inline=False)
    embed.add_field(name="!remove <NAME>", value="音声を削除します", inline=False)
    embed.add_field(name="!list", value="音声一覧を表示します", inline=False)
    embed.add_field(name="!play <URL>", value="YouTube / ニコニコ動画の音声を再生します", inline=False)
    embed.add_field(name="!yarimasune", value="やりますねぇ！", inline=False)

    await ctx.send(embed=embed)

bot.run(api_key)