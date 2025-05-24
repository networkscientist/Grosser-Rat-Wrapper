# basel-politics
## Motivation

There you go!... Initially motivated to create this repo by the now infamous (self-declared) *youngest and most beautiful* member of Basel's parliament, I wanted to get each and every PDF which said member had introduced into Basel's parliament. While it is well-known that said member is a Nazi (this has even been confirmed by a [Swiss court](https://www.srf.ch/news/basel-baselland-rechtsextremer-eric-weber-durfte-als-nazi-bezeichnet-werden)), and while this member's contributions to parliamentary activities are - I am by no means trying to insult the member here - of rather minimal value, he frequently creates viral videos (wether intentionally or not...).

But, to be fair, I have to hand it to the guy: Whenever I feel down I read one of his political initiatives and then I feel... well, I usually start to smile. Although he is dead serious, it sounds like the transcript to a Monty Python sketch. Symptoms, which one might easily associate with a mild depression, they are quickly evaporated. This politician's ideas are so absurd, you are bound to laugh (unless you take him seriously, which I would advise you had better not done).

Therefore; to anyone, who feels called to fight right-wing nazism: Feel free to contribute to this repo. And to those, who don't give a crap about politics, you are welcome to participate in the development of grosser-rat-wrapper, as well :=D

## Updates
### Roadmap Update 20250524

While the original plan was to use a sqlite database to save the data for future use, I realized that I do not currently have enough knowledge about SQL to seriously implement the feature this way. My main expertise is in data analysis; therefore, saving data will currently focus on CSV and Parquet files, perhaps also Deltalake. Metadata will be supported with Frictionless.
If I (or someone else, for that matter) have the necessary skills to safely integrate sqlite as a means of saving data in the future, it will of course be supported again.
For the time being, any methods dealing with the sqlite database will be left in the code, but not developed anymore.
