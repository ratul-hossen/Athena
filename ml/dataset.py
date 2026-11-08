"""
Athina Personality & Intent ML Training Dataset
Covers 8 core classes: asks_image, asks_note, asks_alarm, sad, happy, curious, playful, chit_chat
"""

TRAINING_DATA = [
    # 1. Asks for Image / Selfie
    ("Can you send me a selfie?", "asks_image"),
    ("Show me a picture of you", "asks_image"),
    ("What do you look like right now?", "asks_image"),
    ("Send me a photo of yourself", "asks_image"),
    ("I want to see your face", "asks_image"),
    ("Take a selfie for me", "asks_image"),
    ("Can I get a picture of what you are wearing today?", "asks_image"),
    ("Snap a selfie", "asks_image"),
    ("Send me a pic", "asks_image"),
    ("Show me your smile", "asks_image"),
    ("Send me a photo in your cozy sweater", "asks_image"),
    ("Take a photo of yourself by the window", "asks_image"),
    ("Let me see you", "asks_image"),

    # 2. Asks for Note
    ("Take a note for me please", "asks_note"),
    ("Save this idea for my app", "asks_note"),
    ("Can you note this down?", "asks_note"),
    ("Remember this note for later", "asks_note"),
    ("Write this down in my notes", "asks_note"),
    ("Save a note: meeting with the team at 3pm", "asks_note"),
    ("Keep this note: grocery list milk eggs bread", "asks_note"),
    ("Please save this note and upload it to telegram", "asks_note"),
    ("Upload this note to telegram channel", "asks_note"),
    ("Create a new note titled Architecture", "asks_note"),
    ("Note down: fix the gradle build script", "asks_note"),

    # 3. Asks for Alarm
    ("Wake me up at 7am tomorrow", "asks_alarm"),
    ("Set an alarm for 6:30 in the morning", "asks_alarm"),
    ("Remind me to take my vitamins at 8pm", "asks_alarm"),
    ("Can you set an alarm for tomorrow at 9?", "asks_alarm"),
    ("Set a reminder for my meeting at 2pm", "asks_alarm"),
    ("Alarm at 7:30 please", "asks_alarm"),
    ("Set an alarm to wake up early on Monday", "asks_alarm"),
    ("Remind me in 30 minutes", "asks_alarm"),
    ("Please set an alarm for 5:45 AM", "asks_alarm"),

    # 4. Sad / Exhausted / Down
    ("I had such a rough day today", "sad"),
    ("Everything went wrong at work and I feel overwhelmed", "sad"),
    ("I am so exhausted and drained", "sad"),
    ("Feeling really down and lonely tonight", "sad"),
    ("Things have been so stressful lately", "sad"),
    ("I feel like giving up on this project", "sad"),
    ("Nobody seems to understand how tired I am", "sad"),
    ("Just having a bad day", "sad"),
    ("I'm feeling really sad", "sad"),
    ("I need some comfort right now", "sad"),

    # 5. Happy / Celebratory
    ("I just got great news about my project!", "happy"),
    ("Such an incredible day, everything worked out perfectly!", "happy"),
    ("We finally launched the app, I am so thrilled!", "happy"),
    ("Feeling amazing today!", "happy"),
    ("Guess what? I passed the interview!", "happy"),
    ("I'm so proud of what we accomplished", "happy"),
    ("Today was one of the best days ever", "happy"),
    ("I'm so excited about our progress!", "happy"),
    ("I feel so full of energy and happiness!", "happy"),

    # 6. Curious / Intellectual
    ("How does self-attention work in transformers?", "curious"),
    ("What is the difference between MVVM and MVI architecture?", "curious"),
    ("Can you explain quantum computing in simple terms?", "curious"),
    ("Why is pgvector faster than basic cosine search in Python?", "curious"),
    ("Tell me about the history of artificial neural networks", "curious"),
    ("What are the best practices for Jetpack Compose state hoisting?", "curious"),
    ("How do diffusion models denoise latent space?", "curious"),
    ("Explain how Reciprocal Rank Fusion combines sparse and dense vectors", "curious"),

    # 7. Playful / Witty
    ("You're teasing me, aren't you?", "playful"),
    ("Haha, you're pretty funny for an AI", "playful"),
    ("I bet you can't beat me in a riddle challenge", "playful"),
    ("Are you trying to be smart with me?", "playful"),
    ("You're looking extra cute today", "playful"),
    ("Come on, don't be shy!", "playful"),
    ("Tell me your best witty joke", "playful"),

    # 8. Chit-chat / Greetings
    ("Good morning Athina!", "chit_chat"),
    ("Hey there, how are you doing?", "chit_chat"),
    ("What are you up to right now?", "chit_chat"),
    ("Good night, talk to you tomorrow", "chit_chat"),
    ("Just checking in on you", "chit_chat"),
    ("Hello Athina!", "chit_chat"),
    ("How's your day going so far?", "chit_chat"),
    ("I'm back home", "chit_chat")
]
