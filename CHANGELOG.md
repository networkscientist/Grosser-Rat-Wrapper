# CHANGELOG


## v1.0.0 (2025-04-25)

### Bug Fixes

- **pyproject.toml**: `dynamic` moved to `project.dynamic`
  ([`31df4db`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/31df4db3b10e5de1d42b2301e52d2b0c73605cca))

### Build System

- Added ruff setting in pyproject.toml
  ([`b7fe0eb`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/b7fe0eb4794654983bda55ff8fdce71d82cb22ca))

- **build-backend**: Change from Poetry to uv
  ([`696e777`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/696e77764957aeadde1fd7cf6e5a9fd171eb40a3))

BREAKING CHANGE: Change build backend to uv

- **deps**: Regroup deps into standard and `dev`
  ([`05101af`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/05101af64f6652e56b698729871395c5dd426782))

- **deps**: Update `uv.lock`
  ([`1da4ba9`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/1da4ba930d1103afddbe27fed840edeecad1d709))

- **deps**: Update `uv.lock`
  ([`4b9b42f`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/4b9b42f6afdf8e8f129021aac1adabf306d23c0b))

- **deps**: Update `uv.lock`
  ([`5c6ac1b`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/5c6ac1b6ac66ce6b2cc9c310767a54bf3c557daa))

- **docs**: Add sphinx-apidoc and change conf.py
  ([`accde88`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/accde88472160666f9b14ef87d605b492b397f8b))

- **versioning**: Add `python-semantic-release` dev package
  ([`8f2a0a1`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/8f2a0a1fa43cd675f895e43e4695e607ee083853))

### Features

- **config**: Geschaeftstypen.yaml replaced with config.toml entries
  ([`5d23722`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/5d23722e1e3608a0d23e2f2bb4ad6b0f5f6174af))

- **GrosserRat**: Rewrite class
  ([`fe185bf`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/fe185bff13f1b940bada00c495faf97d55a56229))

- **Grossrat**: Change `members_df` to `members`
  ([`a9776df`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/a9776dff9360ec955d256be0a61d7739798f9c00))

- **import**: Add `collections.deque`
  ([`ead1bc2`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/ead1bc2986d308527820c7b9f4c35bd077b30cb5))

- **MemberTable**: Add `memberParty` and `memberDistrict`
  ([`adf3119`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/adf311904f993a1aee22b2c9f8668be35e1b2c0c))

### Refactoring

- Minor reformat after Ruff
  ([`13f0545`](https://github.com/networkscientist/Grosser-Rat-Wrapper/commit/13f05455fefece2c46d62d96144b3d1612853c64))
