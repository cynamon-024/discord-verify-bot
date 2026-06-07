import os
import discord
from discord.ext import commands
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

VERIFY_CHANNEL_NAME = "verify"
VERIFIED_ROLE_NAME = "Verified"
UNVERIFIED_ROLE_NAME = "Unverified"

# ==================================================
# STUDENT DATABASE CACHE
# ==================================================

students_cache = {}
last_modified = 0


def load_students():
    global students_cache, last_modified

    try:

        current_modified = os.path.getmtime("students.csv")

        if current_modified != last_modified:

            df = pd.read_csv("students.csv")
            df.columns = df.columns.str.strip()

            students_cache = {}

            for _, row in df.iterrows():
                name = str(row["Name"]).strip().lower()
                sid = str(row["StudentID"]).strip()

                students_cache[(name, sid)] = True

            print(
                f"Student database reloaded. "
                f"{len(students_cache)} students loaded."
            )

            last_modified = current_modified

    except PermissionError:
        print("CSV file locked. Using cached data.")

    return students_cache


# ==================================================
# DISCORD SETUP
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():

    # Load database at startup
    load_students()

    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):

    # Ignore bot messages
    if message.author.bot:
        return

    # Only listen in verify channel
    if message.channel.name != VERIFY_CHANNEL_NAME:
        return

    # Get latest student database
    valid_students = load_students()

    parts = message.content.strip().split()

    # ==================================================
    # FORMAT CHECK
    # ==================================================

    if len(parts) < 2:
        await message.channel.send(
            f"❌ {message.author.mention} invalid format.\n"
            f"Use: Firstname Lastname StudentID"
        )
        return

    student_id = parts[-1]
    name = " ".join(parts[:-1]).lower()

    key = (name, student_id)

    # ==================================================
    # SUCCESS CASE
    # ==================================================

    # ==================================================
# SUCCESS CASE
# ==================================================

    if key in valid_students:

        verified_role = discord.utils.get(
            message.guild.roles,
            name=VERIFIED_ROLE_NAME
        )

        unverified_role = discord.utils.get(
            message.guild.roles,
            name=UNVERIFIED_ROLE_NAME
        )

        if verified_role is None:
            await message.channel.send(
                "❌ Verified role not found. Please contact an admin."
            )
            return

        # User is already verified
        if verified_role in message.author.roles:
            await message.channel.send(
                f"⚠️ {message.author.mention} you are already verified."
            )
            await message.delete()
            return

        # Debug role information
        print("BOT TOP ROLE:", message.guild.me.top_role)
        print("TARGET ROLE:", verified_role)
        print("ROLE POSITION:", verified_role.position)
        print(
            "BOT CAN MANAGE:",
            message.guild.me.guild_permissions.manage_roles
        )

        try:

            # Remove Unverified role if present
            if (
                unverified_role is not None
                and unverified_role in message.author.roles
            ):
                await message.author.remove_roles(
                    unverified_role,
                    reason="Student successfully verified"
                )

            # Add Verified role
            await message.author.add_roles(
                verified_role,
                reason="Student successfully verified"
            )

            # Change nickname
            await message.author.edit(
                nick=name.title()
            )

            await message.channel.send(
                f"✅ {message.author.mention} successfully verified!\n"
                f"Welcome to the server! 🎉"
            )

            # Delete verification message
            await message.delete()

        except discord.Forbidden:
            await message.channel.send(
                "❌ I don't have permission to manage roles "
                "or change nicknames."
            )

        except discord.HTTPException as e:
            await message.channel.send(
                f"❌ Discord API error: {e}"
            )

        return

    # ==================================================
    # FAILURE CASE
    # ==================================================

    id_exists = any(
        student_id == sid
        for (_, sid) in valid_students.keys()
    )

    name_exists = any(
        name == n
        for (n, _) in valid_students.keys()
    )

    if not name_exists and not id_exists:

        await message.channel.send(
            f"❌ {message.author.mention} both name and student ID are incorrect."
        )

    elif not name_exists:

        await message.channel.send(
            f"❌ {message.author.mention} name not found in database."
        )

    elif not id_exists:

        await message.channel.send(
            f"❌ {message.author.mention} student ID not found in database."
        )

    else:

        await message.channel.send(
            f"❌ {message.author.mention} name and student ID do not match."
        )


bot.run(os.getenv("DISCORD_TOKEN"))
