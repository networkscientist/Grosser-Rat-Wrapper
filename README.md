### Roadmap Update 20250524

While the original plan was to use a sqlite database to save the data for future use, I realized that I do not currently have enough knowledge about SQL to seriously implement the feature this way. My main expertise is in data analysis; therefore, saving data will currently focus on CSV and Parquet files, perhaps also Deltalake. Metadata will be supported with Frictionless.
If I (or someone else, for that matter) have the necessary skills to safely integrate sqlite as a means of saving data in the future, it will of course be supported again.
For the time being, any methods dealing with the sqlite database will be left in the code, but not developed anymore.
