# 3.0.0 (upcoming)

* Removed `develop` subcommand, you should use extras for defining development dependencies, as they will then be locked
* Removed support for Python 3.7 and 3.8
* Remove all old typed `Dict`, `Optional`, `Tuple`, `List` to new-style typing
* Remove shiv from the project 

## Todo

* use --dry-run for quicker locking
* Add cli argument to lock with specific version