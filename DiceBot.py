import os
import random
import re
import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

# Replace "YOUR-TOKEN-HERE" with your bot token
TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=discord.Intents.all())
previous_rolls = {}

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")

@bot.command(name="prefix", help="Change the bot's command prefix for this server. Example: !prefix $")
@commands.has_permissions(administrator=True)
async def prefix(ctx, new_prefix: str):
    if len(new_prefix) > 3:
        await ctx.send("The command prefix should be no more than 3 characters.")
        return

    bot.command_prefix = new_prefix
    await ctx.send(f"Command prefix changed to '{new_prefix}'.")


def parse_dice_expression(expression):
    match = re.match(r'(\d+)?d(\d+)((?:[+-]\d+)?)', expression)
    if not match:
        return None

    rolls, sides, modifier = match.groups()
    rolls = int(rolls or 1)
    sides = int(sides)
    modifier = int(modifier or 0)

    return rolls, sides, modifier

aliases = {}

@bot.command(name="alias", help="Create, list, or delete aliases for dice expressions. Examples: !alias save stealth 3d6+2; !alias list; !alias delete stealth")
async def alias(ctx, action: str, name: str = None, *dice_expressions: str):
    user_aliases = aliases.setdefault(ctx.author.id, {})

    if action.lower() == "save":
        if not name or not dice_expressions:
            await ctx.send("Please provide an alias name and at least one dice expression.")
            return
        user_aliases[name.lower()] = dice_expressions
        await ctx.send(f"Alias '{name}' saved.")
    elif action.lower() == "list":
        if not user_aliases:
            await ctx.send("You have no saved aliases.")
            return
        formatted_aliases = "\n".join(f"{alias}: {' '.join(expressions)}" for alias, expressions in user_aliases.items())
        await ctx.send(f"Your aliases:\n{formatted_aliases}")
    elif action.lower() == "delete":
        if not name:
            await ctx.send("Please provide an alias name to delete.")
            return
        if name.lower() not in user_aliases:
            await ctx.send(f"No alias named '{name}' found.")
            return
        del user_aliases[name.lower()]
        await ctx.send(f"Alias '{name}' deleted.")
    else:
        await ctx.send("Invalid action. Please use 'save', 'list', or 'delete'.")

@bot.command(name="roll", help="Rolls one or more sets of dice with optional modifiers or aliases, optionally privately. Example: !roll 2d6+2 3d8-1 stealth --private @DM")
async def roll(ctx, *args: str):
    private = "--private" in args
    if private:
        args = list(args)
        args.remove("--private")

    mention_dm = False
    dm_mention = None
    for arg in args:
        if arg.startswith("<@") and arg.endswith(">"):
            mention_dm = True
            dm_mention = arg
            args.remove(arg)
            break

    if not args:
        await ctx.send("Please provide at least one dice expression or alias.")
        return

    user_aliases = aliases.get(ctx.author.id, {})
    all_parsed_expressions = []
    for item in args:
        if item.lower() in user_aliases:
            dice_expressions = user_aliases[item.lower()]
            for expression in dice_expressions:
                parsed_expression = parse_dice_expression(expression)
                if parsed_expression is None:
                    await ctx.send(f"Invalid dice format in alias '{item}': {expression}. Please update your alias.")
                    return
                all_parsed_expressions.append(parsed_expression)
        else:
            parsed_expression = parse_dice_expression(item)
            if parsed_expression is None:
                await ctx.send(f"Invalid dice format: {item}. Please use the format XdY+Z, where X is the number of dice, Y is the number of sides, and Z is an optional modifier.")
                return
            all_parsed_expressions.append(parsed_expression)

    results = []
    for rolls, sides, modifier in all_parsed_expressions:
        if rolls > 100 or sides > 1000:
            await ctx.send("The maximum number of rolls is 100, and the maximum number of sides is 1000.")
            return

        roll_results = [random.randint(1, sides) + modifier for _ in range(rolls)]
        results.append(roll_results)

    user_rolls = previous_rolls.setdefault(ctx.author.id, [])
    user_rolls.append(results)
    formatted_results = " | ".join(", ".join(str(r) for r in roll_set) for roll_set in results)

    if private:
        recipient_list = [ctx.author]
        if mention_dm:
            dm_user = ctx.message.mentions[0]
            recipient_list.append(dm_user)

        for recipient in recipient_list:
            await recipient.send(f"{ctx.author.display_name}: {formatted_results}")
        await ctx.message.delete()
    else:
        await ctx.send(f"{ctx.author.display_name}: {formatted_results}")

@bot.command(name="history", help="Displays the user's dice roll history.")
async def history(ctx):
    user_rolls = previous_rolls.get(ctx.author.id)
    if not user_rolls:
        await ctx.send("You have no previous rolls.")
        return

    formatted_history = "\n".join(
        f"{idx + 1}: " + " | ".join(", ".join(str(r) for r in roll_set) for roll_set in roll_group)
        for idx, roll_group in enumerate(user_rolls)
    )
    await ctx.send(f"Roll history for {ctx.author.display_name}:\n{formatted_history}")

bot.run(TOKEN)
