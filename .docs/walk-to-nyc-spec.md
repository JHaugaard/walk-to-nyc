### Walking to NYC

Simple app, a number of decisions have been made.

See simple mock up @virtual-walk-challenge.html

Simple premise: My daughter, Sara (short blonde hair for emoji) and her friend Mariah (chin-length brown hair for emoji) are planning a trip to NYC, departing on 9/30/26.

They have set the challenge to walk or bike, in preparation, the distance from their town to NYC before departure. Sara from Columbus, OH and Mariah from Asheville, NC

They want to track their progress. The mock up offers a clever way to do this. We will beef it up as follows:

1. Responsive two-user Web app
2. Two users plus admin; Magic Token auth; Token should have the longest life reasonably and safely possible
3. The basic info collected in the mock up is fine
4. The waypoint cities are a nice touch. Let’s keep them
5. Each user should be permitted to “set things up” by entering the number of miles already logged before starting on the app, thereafter it is just logging without any obvious need for user account info.
6. If possible:
   1. Split screen when viewed on computer or tablet.
   2. Left side - logged in user; Right side - the other
   3. Data entry only on the user’s side. Other side is for viewing, accountability, and encouragement.
   4. When responsive to phone size screen - just logged in user and enough functionality to enter a day’s total.
7. Because I’m trying to develop muscle memory we will run this simple app through the full gauntlet of preparation as if it were an app to track orbital telemetry for the next lunar mission. Learn by doing things correctly.
8. Data platforming first
9. Mock up stores data in browser - we wiil use a database schema - likely sqlite
10. Dev locally; conainers
11. Because we can - let’s deploy to fly.io using simple but effective stack
12. This app has a defined life span. Let’s make it easy to take it down and archive when complete, leaving no trace on fly.io
13. Will point to https://walk.haugaard.app that is managed on Cloudflare; gray cloud. So, as we develop keep that prod decision in mind.