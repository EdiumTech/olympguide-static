#!/bin/sh
set -eu
IOS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR="$IOS_DIR/olympguide/Application"
TEST_DIR=$(mktemp -d "${TMPDIR:-/tmp}/olympguide-personal.XXXXXX")
trap 'rm -f "$TEST_DIR/personal-tests"; rmdir "$TEST_DIR"' EXIT
swiftc -swift-version 5 \
  "$APP_DIR/Models/ResponseModels/Personal/PersonalCalendarModel.swift" \
  "$APP_DIR/Models/ResponseModels/Personal/ScholarshipModel.swift" \
  "$APP_DIR/Models/ResponseModels/Personal/RecommendationsModel.swift" \
  "$APP_DIR/Models/ResponseModels/Personal/ApplicantModel.swift" \
  "$APP_DIR/Models/ResponseModels/Benefits/BenefitModel.swift" \
  "$APP_DIR/Models/ResponseModels/Diplomas/DiplomaModel.swift" \
  "$APP_DIR/Models/ResponseModels/Olympiads/OlympiadShortModel.swift" \
  "$APP_DIR/Models/ViewModels/Diplomas/DiplomaViewModel.swift" \
  "$IOS_DIR/tests/personal/main.swift" -o "$TEST_DIR/personal-tests"
"$TEST_DIR/personal-tests"
