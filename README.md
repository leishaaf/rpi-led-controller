# rpi-led-controller
Python code that controls the LED sign in the SCE room

Allows messages to be displayed on an LED sign through a REST API built with Python and FastAPI. Messages can include text, color, scroll speed, and optional expiration dates. TTL expiration ensures messages automatically disappear after the scheduled time.
 
 # My Contribution:

- Built the initial API and message display logic using Python
- Displayed sign messages with the subprocess Python library, created a /status API endpoint to share server state
- Implemented the core TTL expiration by leveraging Locks and Events from the Python threading library to expire a message and prevent race conditions

Mentorship: My mentor polished the code for production safety and maintainability.
