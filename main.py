import discord
from discord.ext import commands, tasks
import os
import requests
from datetime import datetime, timedelta
from extra import prob_value
import time
from threading import Thread


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.leaderboard_result_week = ""
bot.leaderboard_result_month = ""



@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    thread = Thread(target=task)
    thread.start()
    


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
 
 

def read_handles_from_file(file_path="handles.txt"):
    try:
        with open(file_path, "r") as file:
            handles = file.read().splitlines()
        return handles
    except Exception as e:
        print(f"Error reading handles from file: {e}")
        return []
    



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


#inserting handle into handles.txt
async def insert_handle(new_handle, file_path="handles.txt"):
    try:
        with open(file_path, "a") as file:
            file.write(f"{new_handle}\n")
        print(f"Handle '{new_handle}' has been inserted into the file.")
    except Exception as e:
        print(f"Error inserting handle: {e}")
        
        
def is_valid(handle):
    response = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
    return response.json()["status"] == "OK" 

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
        time.sleep(1800)


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


@bot.tree.command()
async def sethandle(inter: discord.Interaction, handle: str): 
    """
    sets handle.
    
    Args:
        handle (str): cf handle
    """
    if is_valid(handle): 
        await insert_handle(handle) 
        await inter.response.send_message(handle + " is registered !") 
        thread = Thread(target=calculate_scores)
        thread.start()
    else: 
        await inter.response.send_message("Invalid handle.", ephemeral=True)


bot.run(os.environ["BOT_TOKEN"])
