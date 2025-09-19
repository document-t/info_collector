{
  "targets": [
    {
      "target_name": "monitor",
      "type": "executable",
      "sources": [
        "monitor.cpp"
      ],
      "libraries": [
        "psapi.lib",
        "ole32.lib"
      ],
      "msvs_settings": {
        "VCCLCompilerTool": {
          "AdditionalOptions": ["/EHsc", "/std:c++17"],
          "WarningLevel": 3
        }
      }
    }
  ]
}
