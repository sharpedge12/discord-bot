import discord
from discord.ext import commands, tasks
import os
import requests
from datetime import datetime, timedelta
from extra import prob_value
import time
from threading import Thread
import pymongo
from pymongo import MongoClient
import json
from keep_alive import keep_alive
import asyncio


# for hosting purposes
keep_alive()


# # getting tokens from environment variables
_token = os.environ.get('token')
_dbtoken = os.environ.get('dbtoken')

# for testing and dev 
# with open("./token.env") as f: 
#         _token = f.read() 

# with open("./db.env") as f: 
#         _dbtoken = f.read() 

# initialising the bot and database
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.leaderboard_result_week = "Results not yet calculated, try again after a while."
bot.leaderboard_result_month = "Results not yet calculated, try again after a while."


cluster = MongoClient(_dbtoken)
db = cluster["bot"]
collection = db["handless"]


# making a new thread that gets called after 30 mins
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    thread = Thread(target=task)
    thread.start()
    
    asyncio.create_task(lbAuto())

    


#calling api and getting the result
def get_cf_ac_submissions(handle, time_period):
    try:
        response = requests.get(f'https://codeforces.com/api/user.status?handle={handle}&from=1&count=100')
        response.raise_for_status()
        submissions = response.json()['result']
        problems = set()
        rating_sum = 0
        
        
        # Get the current time and the timestamp for one/four week ago
        current_time = datetime.now()
        time_delta = current_time - timedelta(weeks=time_period)
        
        # Filter submissions for the last week and accepted verdict
        for submission in submissions:
            cond1 = submission.get('verdict') == 'OK'
            cond2 = datetime.utcfromtimestamp(submission.get('creationTimeSeconds', 0)) >= time_delta
            cond3 = submission.get('problem', {}).get('rating') is not None
            cond4 = f"{submission['problem']['contestId']}{submission['problem']['index']}" not in problems
            if cond1 and cond2 and cond3 and cond4:
                problems.add(f"{submission['problem']['contestId']}{submission['problem']['index']}")
                rating_sum += prob_value[submission['problem']['rating']]
                
        return rating_sum
    except requests.RequestException as error:
        print(f"Error fetching Codeforces submissions for {handle}: {error}")
        return None
    except KeyError as error:
        print(f"KeyError occurred for {handle}: {error}")
        return None
    except Exception as error:
        print(f"An unexpected error occurred for {handle}: {error}")
        return None
 

# see all the handles in db and load them 
def read_handles_from_file():
    handles = []
    for document in collection.find({}, {"_id": 0, "name": 1}):
        handles.append(document["name"])
    return handles 
    



#adding the result and sending it in sorted manner
def get_average_rating_for_handles(time_period):
    handles = read_handles_from_file()
    if not handles:
        print("No handles found in the file.")
        return {}

    results = {}

    for handle in handles:
        rating = get_cf_ac_submissions(handle, time_period)
        if rating:
            results[handle] = rating
        time.sleep(1)  # Introduce a 1-second delay between requests

    sorted_results = dict(sorted(results.items(), key=lambda item: item[1], reverse=True))
    return sorted_results



#formatting the result into string
def format_results(results_map, time):
    formatted_output = ""
    max_name_length = max(len(handle) for handle in results_map.keys())
    
    for i, (handle, rating) in enumerate(results_map.items(), start=1):
        place_indicator = f"{i}{'st🥇' if i == 1 else 'nd🥈' if i == 2 else 'rd🥉' if i == 3 else 'th  ' if (i >= 4 and i <= 9 ) else 'th '}"
        formatted_output += f"{place_indicator.ljust(4)} : {handle.ljust(max_name_length)} - {rating}\n"
        
            
    if time == 1: return f"```Weekly leaderboard\n{formatted_output}```"
    else: return f"```Monthly leaderboard\n{formatted_output}```"


# insert handles into db 
def insert_handle(new_handle):
    new_entry = {"name": new_handle}
    result = collection.insert_one(new_entry)
        
# verifying the handle before inserting
def is_valid(handle):
    response = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
    return response.json()["status"] == "OK" 

# check if organization is as described
def best_org(handle):
    try:
        response = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
        flag = response.json()["organization"] == "Hajmola fan club"
    except Exception as error:
        flag = False
    return flag
        

#calculates leaderboard results
def calculate_scores():
    results_map_week = get_average_rating_for_handles(1)
    if results_map_week: bot.leaderboard_result_week = format_results(results_map_week, 1)
    results_map_month = get_average_rating_for_handles(4)
    if results_map_month: bot.leaderboard_result_month = format_results(results_map_month, 4)
    
# call calculatescore() every 30 mins
def task():
    while True:
        calculate_scores()
        print("the calculations were done")
        time.sleep(1800)

async def lbAuto():
        while True:
            await asyncio.sleep(35*60)
            channel = bot.get_channel(1210084296417878027)
            await channel.purge(limit=None)
            await channel.send(bot.leaderboard_result_week)
            await channel.send(bot.leaderboard_result_month)

# displays the leaderboard when caculated
@bot.tree.command()
async def leaderboard(inter: discord.Interaction, time: str):
    """
    shows leaderboard.
    Args:
        time (str): week/month
    """ 
    final_output = "Results not yet calculated, try again after a while."
    if time.strip() == "week" and bot.leaderboard_result_week: 
        final_output = bot.leaderboard_result_week
    if time.strip() == "month" and bot.leaderboard_result_month: 
        final_output = bot.leaderboard_result_month
    await inter.response.send_message(final_output)


# inserts the handle in database
@bot.tree.command()
async def sethandle(inter: discord.Interaction, handle: str): 
    """
    sets handle.
    
    Args:
        handle (str): cf handle
    """

    if is_valid(handle): 
        result = collection.find_one({"name": handle})
        if result:
            await inter.response.send_message("the handle is already present in the database") 
        else:
            if best_org(handle):
                insert_handle(handle) 
                await inter.response.send_message(handle + " is registered !") 
                thread = Thread(target=calculate_scores)
                thread.start()
            else:
                await inter.response.send_message("Please change your organisation in CF to 'Hajmola fan club' and try again") 
    else: 
        await inter.response.send_message("Invalid handle.")


bot.run(_token)
