from random import uniform
from bpy import context

# This is an easter egg feature intended to be humorous, but if you don't like it, you're welcome to turn it off here:
use_goofy_insults = True
#---------------
# These are displayed when the user is presented with a warning. Though I must admit, ChatGPT is responsible for the conception of many of these brilliant insults.
# Feel free to come up with more and add them, or submit them to me. @theworkshopwarrior on Discord :D

goofy_insults = [
    "Take a deep breath.",
    "How could you do such a thing?",
    "*goofy ahhh music plays*",
    "Try harder next time, dude",
    "You f**ked up badddd.",
    "Simply embarrassing...",
    "Unacceptable.",
    "Why would you do that?",
    "Slow down, man!",
    "Caveman IQ move >:(",
    "Noobie!",
    "Your brain just blue-screened.",
    "Certified goofball moment.",
    "Bro, are you lagging IRL?",
    "That was NOT the move.",
    "Skill issue, for real.",
    "Your WiFi in real life just cut out.",
    "Congratulations, you played yourself.",
    "Biggest L of the century.",
    "That was a tactical failure.",
    "You folded like a lawn chair.",
    "Did your controller disconnect?",
    "404 brain not found.",
    "My disappointment is immeasurable.",
    "You just got nerfed in real-time.",
    "Bro thinks he's in a tutorial.",
    "You just dropped your brain like it's hot.",
    "That move was sponsored by the letter L.",
    "Bro fumbled harder than a Madden AI.",
    "You just got outplayed by a potato.",
    "Your decision-making is on airplane mode.",
    "That was an emotional damage speedrun.",
    "Brain cell count: ERROR 404.",
    "Are you playing with your monitor off?",
    "Bro just got jump-scared by his own actions.",
    "You trippin’ over WiFi signals.",
    "Bro out here making NPC choices.",
    "That was a certified hood classic... of failure.",
    "You really woke up and chose nonsense.",
    "Even Google can’t find logic in that move.",
    # "You moving like a bot programmed in Scratch.",
    "That play was so bad, my RAM crashed.",
    "Bro thinks he's in a sandbox game with no consequences.",
    "Even Clippy wouldn’t know how to help you right now.",
    "You just unlocked a new low score.",
    "This is what happens when you skip the tutorial.",
    "Bro's gameplay looking like a PowerPoint slideshow.",
    "Even your shadow facepalmed."
]

# This is the function used to get a random insult at any time.

def goofy_insult():
    if use_goofy_insults and context.preferences.addons[__name__].preferences.use_goofy_insults:
        return str(goofy_insults[int(uniform(0, len(goofy_insults)))])
    else:
        return ""
