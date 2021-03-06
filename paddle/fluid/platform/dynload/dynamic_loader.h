/* Copyright (c) 2016 PaddlePaddle Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. */

#pragma once

namespace paddle {
namespace platform {
namespace dynload {

/**
 * @brief    load the DSO of CUBLAS
 *
 * @param    **dso_handle   dso handler
 *
 */
void GetCublasDsoHandle(void** dso_handle);

/**
 * @brief    load the DSO of CUDNN
 *
 * @param    **dso_handle   dso handler
 *
 */
void GetCUDNNDsoHandle(void** dso_handle);

/**
 * @brief    load the DSO of CURAND
 *
 * @param    **dso_handle   dso handler
 *
 */
void GetCurandDsoHandle(void** dso_handle);

/**
 * @brief    load the DSO of warp-ctc
 *
 * @param    **dso_handle   dso handler
 *
 */
void GetWarpCTCDsoHandle(void** dso_handle);

/**
 * @brief    load the DSO of lapack
 *
 * @param    **dso_handle   dso handler
 *
 */
void GetLapackDsoHandle(void** dso_handle);

/**
 * @brief    load the DSO of NVIDIA nccl
 *
 * @param    **dso_handle   dso handler
 *
 */
void GetNCCLDsoHandle(void** dso_handle);

}  // namespace dynload
}  // namespace platform
}  // namespace paddle
