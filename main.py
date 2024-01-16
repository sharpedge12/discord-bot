import time 
import lightbulb 
import os 
import math 
from datetime import datetime, timedelta
import random 
import requests
from keep_alive import keep_alive 

# with open("./token.env") as f: 
#         _token = f.read() 

keep_alive()
 
bot = lightbulb.BotApp(token= os.environ.get('token'), default_enabled_guilds=(1053133894897123441, 1180377698808365128)) 

#calling api and getting the result
def get_cf_ac_submissions_last_week(handle):
    try:
        response = requests.get(f'https://codeforces.com/api/user.status?handle={handle}&from=1&count=100')
        response.raise_for_status()
        submissions = response.json()['result']
        
        # Get the current time and the timestamp for one week ago
        current_time = datetime.now()
        one_week_ago = current_time - timedelta(weeks=1)
        
        # Filter submissions for the last week and accepted verdict
        ac_submissions_last_week = [
            submission for submission in submissions    
            if submission.get('verdict') == 'OK'
            and datetime.utcfromtimestamp(submission.get('creationTimeSeconds', 0)) >= one_week_ago
            and submission.get('problem', {}).get('rating') is not None
        ]
        
        # Calculate the sum of problem ratings
        rating_sum = sum(submission['problem']['rating'] for submission in ac_submissions_last_week)
        
        return int(rating_sum / 100)
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
def get_average_rating_for_handles():
    handles = read_handles_from_file()
    if not handles:
        print("No handles found in the file.")
        return {}

    results = {}

    for handle in handles:
        rating = get_cf_ac_submissions_last_week(handle)
        if rating is not None:
            results[handle] = rating
        time.sleep(1)  # Introduce a 1-second delay between requests

    sorted_results = dict(sorted(results.items(), key=lambda item: item[1], reverse=True))
    return sorted_results



#formatting the result into string
def format_results(results_map):
    formatted_output = "```"
    max_name_length = max(len(handle) for handle in results_map.keys())
    
    for i, (handle, rating) in enumerate(results_map.items(), start=1):
        place_indicator = f"{i}{'st🥇' if i == 1 else 'nd🥈' if i == 2 else 'rd🥉' if i == 3 else 'th  ' if (i >= 4 and i <= 9 ) else 'th '}"
        formatted_output += f"{place_indicator.ljust(4)} : {handle.ljust(max_name_length)} - {rating}\n"


    return formatted_output + "```"


#inserting handle into handles.txt
def insert_handle(new_handle, file_path="handles.txt"):
    try:
        with open(file_path, "a") as file:
            file.write(f"{new_handle}\n")
        print(f"Handle '{new_handle}' has been inserted into the file.")
    except Exception as e:
        print(f"Error inserting handle: {e}")


@bot.command 
@lightbulb.command('leaderboard','shows leaderboard ') 
@lightbulb.implements(lightbulb.SlashCommand) 
async def leaderboard(ctx): 
        await ctx.respond("wait , sending....") 
        results_map = get_average_rating_for_handles()
        formatted_output = format_results(results_map)
        await ctx.respond(formatted_output)


@bot.command 
@lightbulb.option("handle" , "enter your codeforces handle here")
@lightbulb.command('sethandle','sets handle for leaderboard , dont be stupid with spelling') 
@lightbulb.implements(lightbulb.SlashCommand) 
async def countdown(ctx : lightbulb.SlashContext) -> None: 
    await ctx.respond("inserting...") 
    insert_handle(ctx.options.handle) 
    await ctx.respond( ctx.options.handle + " is registered !") 
     


 
bot.run()
