# IB_autorader
Opens and closes trades according to strategy specified in Amibroker
  - amibroker explore and scan files located in folder AMI/{strategy}_scan.csv
  - configuration file located in folder confg/settings
    - setIB dictionary: IB API configuration
    - setStrat dictionary: list of Strategies, list of strategy positions open, list of days to close an open position of strategy, Bool to activate Limit order (seed docu)

