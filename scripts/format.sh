#! /bin/bash

black vulcan tests
isort --profile black vulcan tests
