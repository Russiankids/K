import asyncio
import disnake # Changed from discord to disnake
import os # Import os for environment variables if conf.py is not used for TOKEN
from dotenv import load_dotenv # Import load_dotenv if TOKEN is from .env

# --- Configuration (Assumed to be in conf.py or environment variables) ---
# For demonstration purposes, if conf.py is not available,
# you would typically load these from environment variables or direct assignment.
# Let's assume conf.py exists as per the user's original code.
# If conf.py doesn't exist, replace the imports below with direct assignments or
# load from .env using load_dotenv() and os.getenv().

# Example dummy values if conf.py is not used for local testing:
# load_dotenv()
# TOKEN = os.getenv('DISCORD_TOKEN') or 'YOUR_BOT_TOKEN_HERE'
# TO_CHANNEL = int(os.getenv('TO_CHANNEL_ID') or '123456789012345678') # Replace with actual channel ID
# FROM_CHANNELS = [int(id) for id in (os.getenv('FROM_CHANNEL_IDS') or '123456789012345679,123456789012345680').split(',')]
# Verbose = True # Set to False for less console output
# AUTHORIZED_ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID') or '123456789012345681') # Replace with actual user ID

# Assuming conf.py exists and contains these variables:
try:
    from conf import TOKEN, TO_CHANNEL, FROM_CHANNELS, Verbose, AUTHORIZED_ADMIN_USER_ID
except ImportError:
    print("Warning: conf.py not found or incomplete. Attempting to load from environment variables.")
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    TO_CHANNEL = int(os.getenv('TO_CHANNEL_ID', '0')) # Default to 0 if not found
    FROM_CHANNELS = [int(id) for id in os.getenv('FROM_CHANNEL_IDS', '').split(',') if id.strip()]
    Verbose = os.getenv('VERBOSE', 'False').lower() == 'true'
    AUTHORIZED_ADMIN_USER_ID = int(os.getenv('AUTHORIZED_ADMIN_USER_ID', '0'))

    if not TOKEN:
        print("[CRITICAL] DISCORD_TOKEN не найден в переменных окружения. Пожалуйста, установите его.") # Translated
    if not TO_CHANNEL:
        print("[CRITICAL] TO_CHANNEL_ID не найден или недействителен в переменных окружения. Пожалуйста, установите его.") # Translated
    if not FROM_CHANNELS:
        print("[CRITICAL] FROM_CHANNEL_IDS не найдены или недействительны в переменных окружения. Пожалуйста, установите их (через запятую).") # Translated
    if not AUTHORIZED_ADMIN_USER_ID:
        print("[CRITICAL] AUTHORIZED_ADMIN_USER_ID не найден или недействителен в переменных окружения. Пожалуйста, установите его.") # Translated


# --- Bot Setup ---

# Define the necessary intents for the bot.
# Intents are crucial for specifying which events your bot wants to receive from Discord.
# disnake.Intents.default() provides common intents, but for message content,
# disnake.Intents.message_content must be explicitly enabled for non-privileged gateway intents.
# For forwarding messages, at least messages and message_content are needed.
intents = disnake.Intents.default()
intents.messages = True # Required to receive message events
intents.message_content = True # Required to access message.content (privileged intent)
# If your bot interacts with guilds/members, you might need:
# intents.guilds = True
# intents.members = True # Privileged intent, requires enabling in Discord Developer Portal

# Initialize the Disnake client for a standard bot.
# The `self_bot` argument is not supported by disnake's Client class,
# as disnake is designed for regular bot accounts.
client = disnake.Client(intents=intents) # Removed self_bot=True and added intents

# Global variables to store channel objects after the bot logs in.
# This avoids repeatedly fetching channel objects by ID.
to_channel_obj = None
from_channel_objs = {}


@client.event
async def on_ready():
    """
    Called when the bot is ready and connected to Discord.
    This function finds and validates the channels specified in conf.py
    (or environment variables) and caches their objects.
    """
    global to_channel_obj, from_channel_objs

    print("-" * 30)
    print(f"Вошел как {client.user.name}#{client.user.discriminator} (ID: {client.user.id})") # Translated
    print(f"ID авторизованного администратора: {AUTHORIZED_ADMIN_USER_ID}") # Translated
    print("-" * 30)
    print("Поиск и кэширование каналов из вашей конфигурации...") # Translated

    # Attempt to find the configured destination channel.
    to_channel_obj = client.get_channel(TO_CHANNEL)
    if to_channel_obj:
        print(f"[OK] Целевой канал найден: #{to_channel_obj.name} ({to_channel_obj.id})") # Translated
    else:
        print(
            f"[ERROR] Не удалось найти целевой канал с ID: {TO_CHANNEL}. " # Translated
            "Пожалуйста, проверьте ID и убедитесь, что ваша учетная запись может видеть этот канал." # Translated
        )

    # Iterate through the list of source channel IDs and find their objects.
    for channel_id in FROM_CHANNELS:
        channel = client.get_channel(channel_id)
        if channel:
            from_channel_objs[channel_id] = channel
            print(f"[OK] Прослушивание исходного канала: #{channel.name} ({channel.id})") # Translated
        else:
            print(f"[ERROR] Не удалось найти исходный канал с ID: {channel_id}. Он будет проигнорирован.") # Translated

    # Critical check: If no destination or source channels are found,
    # inform the user that the bot cannot function correctly.
    if not to_channel_obj or not from_channel_objs:
        print(
            "\n[CRITICAL] Бот не сможет пересылать сообщения из-за ошибок конфигурации канала. " # Translated
            "Пожалуйста, исправьте ID в conf.py (или переменных окружения) и перезапустите." # Translated
        )
    else:
        print("\nБот запущен и прослушивает сообщения.") # Translated
    print("-" * 30)


@client.event
async def on_message(message: disnake.Message): # Changed from discord.Message to disnake.Message
    """
    Processes incoming messages from any channel the bot can see.
    This function handles both the `!resend_channel` command and
    standard message forwarding.
    """
    # Important: Prevent the bot from reacting to its own messages to avoid loops.
    if message.author == client.user:
        return

    # Optional: Print verbose message reception information.
    if Verbose:
        print(f"-> Сообщение получено в #{message.channel.name} от {message.author.name}") # Translated

    # --- !resend_channel Command Logic ---
    # This command allows an authorized admin to resend messages from a specified
    # source channel to the configured destination channel.
    if message.content.lower().startswith('!resend_channel'):
        # Check if the message author is the authorized admin.
        if message.author.id != AUTHORIZED_ADMIN_USER_ID:
            if Verbose:
                print(f"-> Несанкционированное использование !resend_channel от {message.author.name} (ID: {message.author.id})") # Translated
            await message.channel.send("🚫 Вы не авторизованы использовать эту команду.") # Translated
            return

        try:
            # Parse the command arguments: channel ID and optional number of messages.
            # Strips '<#>' from channel mentions to get the raw ID.
            parts = message.content.split()
            target_resend_channel_id = int(parts[1].strip('<#>'))
            # Default to 100 messages if not specified, limit to 200.
            num_messages_to_resend = int(parts[2]) if len(parts) > 2 else 100
            if num_messages_to_resend > 200:
                num_messages_to_resend = 200
            if num_messages_to_resend < 1:
                num_messages_to_resend = 1
        except (ValueError, IndexError):
            # Inform the user about incorrect command usage.
            await message.channel.send("⚠️ Неверный формат. Использование: `!resend_channel <channel_id> [num_messages]`") # Translated
            return

        # Fetch the source channel object for the resend operation.
        source_channel = client.get_channel(target_resend_channel_id)
        if not source_channel:
            await message.channel.send(f"❌ Не удалось найти исходный канал с ID {target_resend_channel_id}.") # Translated
            return
        # Ensure the destination channel is configured.
        if not to_channel_obj:
            await message.channel.send("❌ Целевой канал настроен некорректно. Проверьте логи.") # Translated
            return

        print(f"Попытка переслать {num_messages_to_resend} сообщений из канала: {source_channel.name}") # Translated
        await message.channel.send(f"🔄 Извлечение {num_messages_to_resend} сообщений из {source_channel.mention}...") # Translated

        try:
            # Determine the guild name for context.
            source_guild_name = source_channel.guild.name if source_channel.guild else "Личное сообщение" # Translated
            # Fetch message history from the source channel, oldest first.
            async for msg_to_resend in source_channel.history(limit=num_messages_to_resend, oldest_first=True):
                # Construct the forwarded message content with origin information.
                forwarded_msg_content = (
                    f'🤖[Переслано от **{msg_to_resend.author}** в `{source_guild_name}/{source_channel.name}`]\n' # Translated
                    f'{msg_to_resend.content}'
                )
                await to_channel_obj.send(forwarded_msg_content)

                # Forward attachments and embeds.
                for attachment in msg_to_resend.attachments:
                    await to_channel_obj.send(attachment.url)
                for embed in msg_to_resend.embeds:
                    if embed.url: # Only send URL if present for a basic embed forwarding
                        await to_channel_obj.send(embed.url)
                await asyncio.sleep(1) # Small delay to avoid rate limits.

            await message.channel.send(
                f"✅ Завершено пересылка сообщений из {source_channel.mention} в {to_channel_obj.mention}." # Translated
            )
            print("\t> Все исторические сообщения пересланы.") # Translated
        except disnake.Forbidden: # Changed from discord.Forbidden to disnake.Forbidden
            # Handle cases where the bot lacks permission to read history.
            await message.channel.send(
                f"❌ У меня нет разрешения читать историю сообщений в {source_channel.mention}." # Translated
            )
        except Exception as e:
            # Catch any other unexpected errors during resend.
            await message.channel.send(f"❌ Произошла непредвиденная ошибка во время пересылки: {e}") # Translated
            print(f"Ошибка при пересылке: {e}") # Translated
        return # Exit the function after handling the command.

    # --- Standard Message Forwarding Logic ---
    # This logic applies if the message is not a command and is from a configured source channel.
    # Check if the message's channel ID is in our list of `FROM_CHANNELS`
    # and if the `to_channel_obj` is properly configured.
    if message.channel.id not in from_channel_objs or not to_channel_obj:
        return # Do nothing if not a source channel or destination is missing.

    # Determine the server name for contextual forwarding.
    server_name = message.guild.name if message.guild else "Личное сообщение" # Translated
    # Construct the forwarded message content.
    forward_msg_content = f'🤖**{message.author}** из `{server_name}/{message.channel.name}`\n{message.content}' # Translated

    # Send the message to the destination channel.
    await to_channel_obj.send(forward_msg_content)
    if Verbose:
        print(f"  > Сообщение переслано от {message.author.name} в #{message.channel.name}") # Translated

    # Forward any attachments and embeds that came with the original message.
    for attachment in message.attachments:
        await to_channel_obj.send(attachment.url)
    for embed in message.embeds:
        if embed.url: # Only send URL if present for a basic embed forwarding
            await to_channel_obj.send(embed.url)


if __name__ == '__main__':
    print("Бот запускается...") # Translated
    try:
        # Attempt to run the bot with the provided token.
        client.run(TOKEN)
    except disnake.errors.LoginFailure: # Changed from discord.errors.LoginFailure to disnake.errors.LoginFailure
        # Catch specific login failure errors (e.g., invalid token).
        print("\n[CRITICAL] Ошибка входа: Недействительный токен. Пожалуйста, проверьте ваш файл `conf.py` или переменные окружения.") # Translated
    except Exception as e:
        # Catch any other unhandled exceptions during bot execution.
        print(f"\n[CRITICAL] Произошла непредвиденная ошибка во время работы бота: {e}") # Translated

