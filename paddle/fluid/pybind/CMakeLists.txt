set(PYBIND_DEPS pybind python proto_desc memory executor fleet_wrapper box_wrapper prune
  feed_fetch_method pass generate_pass pass_builder parallel_executor profiler layer tracer engine scope_pool
  analysis_predictor imperative_profiler imperative_flag save_load_util dlpack_tensor device_context
  gloo_wrapper infer_io_utils heter_wrapper generator op_version_registry ps_gpu_wrapper custom_operator
  cost_model cuda_graph_with_memory_pool fleet_executor)

if (WITH_PSCORE)
  set(PYBIND_DEPS ${PYBIND_DEPS} ps_service)
  set(PYBIND_DEPS ${PYBIND_DEPS} graph_py_service)
endif()
if (WITH_GPU OR WITH_ROCM)
  set(PYBIND_DEPS ${PYBIND_DEPS} dynload_cuda)
  set(PYBIND_DEPS ${PYBIND_DEPS} cuda_device_guard)
endif()

if (WITH_GPU)
  set(PYBIND_DEPS ${PYBIND_DEPS} cuda_profiler)
endif()

if (WITH_NCCL OR WITH_RCCL)
  set(PYBIND_DEPS ${PYBIND_DEPS} nccl_wrapper)
  set(PYBIND_DEPS ${PYBIND_DEPS} reducer)
endif()

if (WITH_XPU_BKCL)
  set(PYBIND_DEPS ${PYBIND_DEPS} reducer)
  set(PYBIND_DEPS ${PYBIND_DEPS} bkcl_context)
endif()

if(NOT WIN32)
  set(PYBIND_DEPS ${PYBIND_DEPS} data_loader)
  set(PYBIND_DEPS ${PYBIND_DEPS} mmap_allocator)
  if (WITH_NCCL OR WITH_RCCL)
    set(PYBIND_DEPS ${PYBIND_DEPS} nccl_context)
  endif()
endif(NOT WIN32)

if(WITH_PYTHON)
  list(APPEND PYBIND_DEPS py_func_op)
  list(APPEND PYBIND_DEPS py_layer_op)
endif()

set(PYBIND_SRCS
  pybind.cc
  exception.cc
  protobuf.cc
  const_value.cc
  global_value_getter_setter.cc
  reader_py.cc
  fleet_wrapper_py.cc
  heter_wrapper_py.cc
  ps_gpu_wrapper_py.cc
  gloo_wrapper_py.cc
  box_helper_py.cc
  data_set_py.cc
  imperative.cc
  ir.cc
  bind_cost_model.cc
  bind_fleet_executor.cc
  inference_api.cc
  compatible.cc
  io.cc
  generator_py.cc
  cuda_streams_py.cc)

if(WITH_ASCEND)
  set(PYBIND_DEPS ${PYBIND_DEPS} ascend_wrapper)
  set(PYBIND_SRCS ${PYBIND_SRCS} ascend_wrapper_py.cc)
endif()

if(WITH_GLOO)
  set(PYBIND_DEPS ${PYBIND_DEPS} gloo_context)
  set(PYBIND_SRCS ${PYBIND_SRCS} gloo_context_py.cc)
  set(PYBIND_DEPS ${PYBIND_DEPS} imperative_gloo_context)
  set(PYBIND_DEPS ${PYBIND_DEPS} reducer)
endif(WITH_GLOO)

if (WITH_CRYPTO)
  set(PYBIND_DEPS ${PYBIND_DEPS} paddle_crypto)
  set(PYBIND_SRCS ${PYBIND_SRCS} crypto.cc)
endif (WITH_CRYPTO)

if (WITH_PSLIB)
  set(DISTRIBUTE_COMPILE_FLAGS "-Wno-non-virtual-dtor -Wno-error=non-virtual-dtor -Wno-error=delete-non-virtual-dtor -Wno-error=sign-compare -Wno-error=unused-variable -Wno-error=return-type -Wno-error=unused-but-set-variable -Wno-error=type-limits -Wno-error=unknown-pragmas -Wno-error=parentheses -Wno-error=unused-result")
  if (CMAKE_CXX_COMPILER_VERSION VERSION_GREATER 7.0)
      set(DISTRIBUTE_COMPILE_FLAGS
              "${DISTRIBUTE_COMPILE_FLAGS} -faligned-new")
  endif()
  set_source_files_properties(heter_wrapper_py.cc PROPERTIES COMPILE_FLAGS ${DISTRIBUTE_COMPILE_FLAGS})
endif(WITH_PSLIB)
if (WITH_PSCORE)
  set(DISTRIBUTE_COMPILE_FLAGS "-Wno-non-virtual-dtor -Wno-error=non-virtual-dtor -Wno-error=delete-non-virtual-dtor -Wno-error=sign-compare -Wno-error=unused-variable -Wno-error=return-type -Wno-error=unused-but-set-variable -Wno-error=type-limits -Wno-error=unknown-pragmas -Wno-error=parentheses -Wno-error=unused-result")
  set_source_files_properties(fleet_py.cc PROPERTIES COMPILE_FLAGS ${DISTRIBUTE_COMPILE_FLAGS})
  list(APPEND PYBIND_DEPS fleet communicator index_wrapper index_sampler)
  list(APPEND PYBIND_SRCS fleet_py.cc)
endif()

if (WITH_NCCL OR WITH_RCCL)
  list(APPEND PYBIND_SRCS nccl_wrapper_py.cc)
endif()

if(WITH_PYTHON)
  # generate op pybind functions automatically for dygraph.
  if (WITH_ASCEND_CL)
    set(OP_FUNCTION_GENERETOR_DEPS pybind proto_desc executor layer tracer engine imperative_profiler imperative_flag ascend_wrapper)
  else()
    set(OP_FUNCTION_GENERETOR_DEPS pybind proto_desc executor layer tracer engine imperative_profiler imperative_flag)
  endif()
  list(APPEND OP_FUNCTION_GENERETOR_DEPS ${GLOB_OP_LIB})
  list(APPEND OP_FUNCTION_GENERETOR_DEPS ${GLOB_OPERATOR_DEPS})

  if (WITH_NCCL OR WITH_RCCL)
    list(APPEND OP_FUNCTION_GENERETOR_DEPS nccl_context)
  endif()

  if(WITH_XPU_BKCL)
    list(APPEND OP_FUNCTION_GENERETOR_DEPS bkcl_context)
  endif(WITH_XPU_BKCL)

  add_executable(op_function_generator op_function_generator.cc)
  target_link_libraries(op_function_generator ${OP_FUNCTION_GENERETOR_DEPS})

  get_property (os_dependency_modules GLOBAL PROPERTY OS_DEPENDENCY_MODULES)
  target_link_libraries(op_function_generator ${os_dependency_modules})
  if(WITH_ROCM)
    target_link_libraries(op_function_generator ${ROCM_HIPRTC_LIB})
  endif()

  set(impl_file ${CMAKE_SOURCE_DIR}/paddle/fluid/pybind/op_function_impl.h)
  set(tmp_impl_file ${impl_file}.tmp)

  set(OP_IMPL_DEPS op_function_generator)
  if(WIN32)
    if("${CMAKE_GENERATOR}" STREQUAL "Ninja")
      set(op_impl_path "${CMAKE_CURRENT_BINARY_DIR}")
    else()
      set(op_impl_path "${CMAKE_CURRENT_BINARY_DIR}/${CMAKE_BUILD_TYPE}")
    endif()

    file(WRITE ${CMAKE_BINARY_DIR}/paddle/fluid/pybind/op_function_generator_retry.bat ""
    "set build_times=1\n"
    ":retry\n"
    "ECHO op_function_generator run %build_times% time\n"
    "taskkill /f /im op_function_generator.exe 2>NUL\n"
    "${op_impl_path}/op_function_generator.exe ${tmp_impl_file}\n"
    "if %ERRORLEVEL% NEQ 0 (\n"
    "    set /a build_times=%build_times%+1\n"
    "    if %build_times% GEQ 10 (\n"
    "        exit /b 1\n"
    "    ) else (\n"
    "        goto :retry\n"
    "    )\n"
    ")\n"
    "exit /b 0")

    if(${CBLAS_PROVIDER} STREQUAL MKLML)
      ADD_CUSTOM_COMMAND(OUTPUT ${op_impl_path}/libiomp5md.dll
        COMMAND ${CMAKE_COMMAND} -E copy ${MKLML_SHARED_IOMP_LIB} ${op_impl_path}
        DEPENDS mklml)
      list(APPEND OP_IMPL_DEPS ${op_impl_path}/libiomp5md.dll)
    else(${CBLAS_PROVIDER} STREQUAL EXTERN_OPENBLAS)
      ADD_CUSTOM_COMMAND(OUTPUT ${op_impl_path}/openblas.dll
        COMMAND ${CMAKE_COMMAND} -E copy ${OPENBLAS_SHARED_LIB} ${op_impl_path}
        DEPENDS extern_openblas)
      list(APPEND OP_IMPL_DEPS ${op_impl_path}/openblas.dll)
    endif()
    if(WITH_MKLDNN)
      ADD_CUSTOM_COMMAND(OUTPUT ${op_impl_path}/mkldnn.dll
        COMMAND ${CMAKE_COMMAND} -E copy ${MKLDNN_SHARED_LIB} ${op_impl_path}
        DEPENDS mkldnn)
        list(APPEND OP_IMPL_DEPS ${op_impl_path}/mkldnn.dll)
    endif()

    add_custom_command(OUTPUT ${impl_file}
      COMMAND ${CMAKE_BINARY_DIR}/paddle/fluid/pybind/op_function_generator_retry.bat
      COMMAND ${CMAKE_COMMAND} -E copy_if_different ${tmp_impl_file} ${impl_file}
      COMMENT "copy_if_different ${tmp_impl_file} to ${impl_file}"
      DEPENDS ${OP_IMPL_DEPS})
  else(WIN32)
    # If there are no *.so in /usr/lib or LD_LIBRARY_PATH,
    # copy these *.so to current directory and append current directory to
    # LD_LIBRARY_PATH. This is different with Windows platformm, which search
    # *.dll in current directory automatically.
    if(WITH_MKLML)
      ADD_CUSTOM_COMMAND(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/libiomp5.so
        COMMAND ${CMAKE_COMMAND} -E copy ${MKLML_SHARED_IOMP_LIB} ${CMAKE_CURRENT_BINARY_DIR}
        DEPENDS mklml)
      list(APPEND OP_IMPL_DEPS ${CMAKE_CURRENT_BINARY_DIR}/libiomp5.so)
    endif()
    if(WITH_MKLDNN)
      ADD_CUSTOM_COMMAND(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/libdnnl.so.0
        COMMAND ${CMAKE_COMMAND} -E copy ${MKLDNN_SHARED_LIB} ${CMAKE_CURRENT_BINARY_DIR}
        DEPENDS mkldnn)
      list(APPEND OP_IMPL_DEPS ${CMAKE_CURRENT_BINARY_DIR}/libdnnl.so.0)
    endif()
    add_custom_command(OUTPUT ${impl_file}
          COMMAND ${CMAKE_COMMAND} -E env "LD_LIBRARY_PATH=$ENV{LD_LIBRARY_PATH}:."
              "${CMAKE_CURRENT_BINARY_DIR}/op_function_generator"
              "${tmp_impl_file}"
          COMMAND ${CMAKE_COMMAND} -E copy_if_different ${tmp_impl_file} ${impl_file}
          COMMENT "copy_if_different ${tmp_impl_file} to ${impl_file}"
          DEPENDS ${OP_IMPL_DEPS}
          VERBATIM)
  endif(WIN32)
  add_custom_target(op_function_generator_cmd ALL DEPENDS ${impl_file})

  list(APPEND PYBIND_DEPS interpretercore standalone_executor)
  cc_library(paddle_pybind SHARED
    SRCS ${PYBIND_SRCS}
    DEPS ${PYBIND_DEPS} ${GLOB_OP_LIB} ${GLOB_OPERATOR_DEPS})

  if(NOT APPLE AND NOT WIN32)
    target_link_libraries(paddle_pybind rt)
  endif(NOT APPLE AND NOT WIN32)

  if(WITH_ROCM)
    target_link_libraries(paddle_pybind ${ROCM_HIPRTC_LIB})
  endif()

  get_property (os_dependency_modules GLOBAL PROPERTY OS_DEPENDENCY_MODULES)
  target_link_libraries(paddle_pybind ${os_dependency_modules})
  add_dependencies(paddle_pybind op_function_generator_cmd)
endif(WITH_PYTHON)
