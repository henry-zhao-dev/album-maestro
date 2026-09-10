# Example album specifications

Album Maestro stores its catalog in SQLite. These JSON files are example album
specifications for import and local processing. The matching demo audio can be
downloaded locally from the linked Wikimedia Commons pages; the audio files
are intentionally not committed to the repository.

Create a library and add album records through the CLI:

```shell
album-maestro init ~/Music/album-maestro-example
album-maestro create --library ~/Music/album-maestro-example
album-maestro list --library ~/Music/album-maestro-example
```

Download the optional demo audio sources from Wikimedia Commons. Run these
commands from the repository root:

```shell
mkdir -p examples/sources

curl --fail --location --output examples/sources/beethoven-symphony-no-5-i.ogg \
  "https://commons.wikimedia.org/wiki/Special:FilePath/Ludwig_van_Beethoven_-_symphony_no._5_in_c_minor,_op._67_-_i._allegro_con_brio.ogg"
curl --fail --location --output examples/sources/beethoven-symphony-no-5-ii.ogg \
  "https://commons.wikimedia.org/wiki/Special:FilePath/Ludwig_van_Beethoven_-_symphony_no._5_in_c_minor,_op._67_-_ii._andante_con_moto.ogg"
curl --fail --location --output examples/sources/beethoven-symphony-no-5-iii.ogg \
  "https://commons.wikimedia.org/wiki/Special:FilePath/Ludwig_van_Beethoven_-_symphony_no._5_in_c_minor,_op._67_-_iii._allegro.ogg"
curl --fail --location --output examples/sources/beethoven-symphony-no-5-iv.ogg \
  "https://commons.wikimedia.org/wiki/Special:FilePath/Ludwig_van_Beethoven_-_symphony_no._5_in_c_minor,_op._67_-_iv._allegro.ogg"
curl --fail --location --output examples/sources/mozart-piano-sonata-no-11-iii.ogg \
  "https://commons.wikimedia.org/wiki/Special:FilePath/Mozart-Marsz_turecki-(Romuald_Greiss).ogg"
curl --fail --location --output examples/sources/boccherini-minuet.ogg \
  "https://commons.wikimedia.org/wiki/Special:FilePath/Boccerini_Op11_n%C2%B05_G275_Satz3_Minuett.ogg"

cp examples/sources/*.ogg ~/Music/album-maestro-example/sources/
```

The JSON `url` values point to the source pages for the recordings and are
retained as catalog metadata. The file-level provenance and licensing details
are documented in [`sources/ATTRIBUTION.md`](sources/ATTRIBUTION.md).

Import an example album into SQLite with:

```shell
album-maestro import --json albums/beethoven-symphony-no-5.json \
  --library ~/Music/album-maestro-example
```

Or import every example album at once:

```shell
album-maestro import --directory albums \
  --library ~/Music/album-maestro-example
```

Process the Beethoven example into tagged track files:

```shell
album-maestro process symphony-no-5 \
  --library ~/Music/album-maestro-example
```

Process the Classical Favorites example:

```shell
album-maestro process classical-favorites \
  --library ~/Music/album-maestro-example
```

Export an imported album back to JSON with:

```shell
album-maestro export symphony-no-5 \
  --json beethoven-symphony-no-5.json \
  --library ~/Music/album-maestro-example
```
