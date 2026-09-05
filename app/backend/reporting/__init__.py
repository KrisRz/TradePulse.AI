"""Offline reporting tools. Deliberately outside the Lambda packages.

Nothing here runs on the trading path, and the build script does not ship it —
`build_lambda_package.sh` copies only `paper_trading` and `backtesting`. A tax
report is something a person runs once a year on a laptop, and code that never
reaches production cannot break production.
"""
