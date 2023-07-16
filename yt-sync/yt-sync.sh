while read p; do
	[[ $p =~ ^#.* ]] && continue
	simulation="-s --get-filename" # insert into ytdlp to simulate filename outputs
	disk_location=$(echo "$p" | cut -f2 | sed 's/ /_/g')
	channel=$(echo "$p" | cut -f1)
	extra_args=$(echo "$p" | cut -f3-)
	echo "Syncing channel $channel at disk location $disk_location, with extra args $extra_args"
	yt-dlp --all-subs $extra_args --download-archive archive.txt -o $disk_location $channel
done <config.tsv
