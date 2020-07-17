# QToZero

## Welcome

QtoZero is a project that supports some of the custom rule sets that the Calvinball Fantasy Football league has implemented. We have a lot of rules, (like, a _lot_ of rules) and most commercially available fantasy football websites do not fully support what we do. The main point of this project is to fill in those gaps.

If you're interested in less about _what_ this project is and more about the person and process for maintaining this project, feel free to jump to the [Project History](#history) section.

## What's the point of this project?

In Calvinball Fantasy Football we have made so many sweet, awesome rules that make this the most fun league to participate it that we were flooded with trying to keep track of everything. This project aims to help that out.

The website portion is geared toward facilitating our offseason player acquisition program known as Restricted Free Agency (RFA). At the heart of that is a database where we keep information about our franchise owners and the players on those rosters.

We use www.myfantasyleague.com (MFL)as our base fantasy football provider due to its customization as well as its easy to comprehend and use API. I will attempt to document all the things this project and website aim to do.

Then there are a bunch of scripts that get run on a schedule to handle a few other housekeeping tasks during the season. Mainly we try to:

- Keep track of how many times owners played 2 quarterbacks (they're only allowed 6 chances)
- Monitor roster violations (we allow flexibility in the MFL site to make sure trades and transactions can go through, but we do have a salary cap and do have roster size limits.)

In 2018 we added a feature to the league where Week 17 was Pro Bowl Week, where owners would try to make up the best possible lineup for the week using players from within their own Calvinball divisions. The website handles that aspect as well.

## <a name="history"></a>Project History

Back in 2014-ish I decided I wanted to learn and stretch myself with some web technologies I hadn't used before and settled on learning Flask. I followed along with the first edition of Miguel Grinberg's wonderful Flask book to get myself started, and then decided to try to improve upon my ridiculous fantasy football league's off-season "Restricted Free Agency". We made up all these off-season roster rules, and then were tracking and managing things via email.

After getting the RFA stuff working (mostly, there were always bugs) I started to take aim at doing some stuff automatically during the season to help track some of our other rules. For example we let you play two QBs a week, but only 6 times during the season. So I made a QB tracker and would have a bot post on our league Slack channel each week with everyone's 2 QB playing status.

From the very first season to now I've taken aim at improving one thing each year. On the backend I've swiched from serving up with Apache2 to using gunicorn and Nginx. I've tried to refactor the code a bit each year so I hate myself just a little less for the code I wrote 5 years prior.

I think its an ugly site with only marginal usability and every time I come back to the code I think "What was I thinking!?" But, I only work on this project once every six months or so and it has proven a nice opportunity for me to come back as I've progressed in my software experience and make small iterative improvments. Each year I'm not quite as upset at myself for what I wrote than I was the year before, so... progress? There's a lot more I'd like to do, but I just don't prioritize it all the time. Because its fantasy football.
