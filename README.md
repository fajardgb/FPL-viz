# FPL-viz

FPL Helpful Visualizations

As the Admin of a Fantasy Premier League (FPL) league, I created a few informative tools to make the experience more enjoyable. 

Lots of thanks to Jack Somervell and his article [A Complete Guide to the Fantasy Premier League (FPL) API](https://www.game-change.co.uk/2023/02/10/a-complete-guide-to-the-fantasy-premier-league-fpl-api/)!

## First, we need to get the data for the league (and it's users)
All we need is the league ID, which can be found like so:

To get league ID: Fantasy -> Leagues and Cups -> select your league

league_id = **numbers before "/standings/"** in the URL

ie: for my league, the URL is https://fantasy.premierleague.com/leagues/736795/standings/c, so my league ID would be "736795".

### Get league data

Once we have the league ID, we can use the ```save_league_data``` function to fetch our league's data. 

### Get user data

From our saved league data, we can get individual manager/user data using the ```get_users``` function

This function also saves the manager name and ID of the user data as a pickle dictionary (**entry_to_player_dict.pickle**). 

### Get user data across time

Using the ```entry_to_player_dict.pickle``` dictionary, we can get the user data across the course of the league. In other words, we can get the number of points for each gameweek. 

Fetch the history data by using the ```fetch_and_save_history``` function. Make a df of this data using the ```get_gw_history_df``` function. 

## Plotting Standings

### Plot current standings

Use the ```plot_current_standings``` function!

![current_standings](imgs/current_standings.png)

### Lineplot of standings across the season

Use the ```lineplot_gw_history``` function

![line_plot_gw_history](imgs/history_lineplot.png)

### Bar chart race of standings across the season

Use the ```bar_chart_race_gw_history``` function! 

Note: the packages may be tricky to install. 

![bar_chart_race_gw_history](imgs/league_736795_bar_chart_race.mp4)

## Let's get Gameweek specific info

- chip usage
- captaincy
- most owned players

Let's first set the gameweek (```GW```) we want to look at. 

### Current GW chip data

Use the ```plot_active_chips``` function!

![active_chips](imgs/active_chips.png)

### Captaincy for current GW

Use the ```plot_captaincy``` function!

![captaincy](imgs/captaincy.png)

### Most owned players

Use the ```plot_most_owned``` function!

![most_owned](imgs/most_owned.png)

