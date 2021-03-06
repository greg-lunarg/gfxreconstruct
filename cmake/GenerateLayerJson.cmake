# Generate the JSON file for this library
function(GENERATE_LAYER_JSON_FILE TARGET LAYER_BINARY IN_FILE OUT_FILE)
    # The output file needs Unix "/" separators or Windows "\" separators
    # On top of that, Windows separators actually need to be doubled because the json format uses backslash escapes
    file(TO_NATIVE_PATH "./" RELATIVE_PATH_PREFIX)
    string(REPLACE "\\" "\\\\" RELATIVE_PATH_PREFIX "${RELATIVE_PATH_PREFIX}")

    # Run each .json.in file through the generator
    # We need to create the generator.cmake script so that the generator can be run at compile time, instead of configure time
    # Running at compile time lets us use cmake generator expressions (TARGET_FILE_NAME and TARGET_FILE_DIR, specifically)
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generator.cmake" "configure_file(\"\${INPUT_FILE}\" \"\${OUTPUT_FILE}\")")

    set(CONFIG_DEFINES
        -DINPUT_FILE="${IN_FILE}"
        -DVK_VERSION="${VULKAN_VERSION_MAJOR}.${VULKAN_VERSION_MINOR}.${VULKAN_VERSION_PATCH}"
        -DOUTPUT_FILE="${OUT_FILE}"
        -DRELATIVE_LAYER_BINARY="${RELATIVE_PATH_PREFIX}${LAYER_BINARY}"
    )
    add_custom_target(${TARGET} ALL COMMAND ${CMAKE_COMMAND} ${CONFIG_DEFINES} -P "${CMAKE_CURRENT_BINARY_DIR}/generator.cmake")
endfunction()


