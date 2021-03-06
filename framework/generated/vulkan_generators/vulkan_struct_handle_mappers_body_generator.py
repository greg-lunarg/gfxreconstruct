#!/usr/bin/python3 -i
#
# Copyright (c) 2019 Valve Corporation
# Copyright (c) 2019 LunarG, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os,re,sys
from base_generator import *

class VulkanStructHandleMappersBodyGeneratorOptions(BaseGeneratorOptions):
    """Options for generating functions to map Vulkan struct member handles at file replay"""
    def __init__(self,
                 blacklists = None,         # Path to JSON file listing apicalls and structs to ignore.
                 platformTypes = None,      # Path to JSON file listing platform (WIN32, X11, etc.) defined types.
                 filename = None,
                 directory = '.',
                 prefixText = '',
                 protectFile = False,
                 protectFeature = True):
        BaseGeneratorOptions.__init__(self, blacklists, platformTypes,
                                      filename, directory, prefixText,
                                      protectFile, protectFeature)

# VulkanStructHandleMappersBodyGenerator - subclass of BaseGenerator.
# Generates C++ functions responsible for mapping struct member handles
# when replaying decoded Vulkan API call parameter data.
class VulkanStructHandleMappersBodyGenerator(BaseGenerator):
    """Generate C++ functions for Vulkan struct member handle mapping at file replay"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        BaseGenerator.__init__(self,
                               processCmds=True, processStructs=True, featureBreak=False,
                               errFile=errFile, warnFile=warnFile, diagFile=diagFile)

        # Map of Vulkan structs containing handles to a list values for handle members or struct members
        # that contain handles (eg. VkGraphicsPipelineCreateInfo contains a VkPipelineShaderStageCreateInfo
        # member that contains handles).
        self.structsWithHandles = dict()
        self.pNextStructs = dict()          # Map of Vulkan structure types to sType value for structs that can be part of a pNext chain.
        # List of structs containing handles that are also used as output parameters for a command
        self.outputStructsWithHandles = []

    # Method override
    def beginFile(self, genOpts):
        BaseGenerator.beginFile(self, genOpts)

        write('#include "generated/generated_vulkan_struct_handle_mappers.h"', file=self.outFile)
        self.newline()
        write('#include "decode/custom_vulkan_struct_decoders.h"', file=self.outFile)
        write('#include "generated/generated_vulkan_struct_decoders.h"', file=self.outFile)
        self.newline()
        write('#include <algorithm>', file=self.outFile)
        self.newline()
        write('GFXRECON_BEGIN_NAMESPACE(gfxrecon)', file=self.outFile)
        write('GFXRECON_BEGIN_NAMESPACE(decode)', file=self.outFile)

        # Implement a utility function to be used for mapping arrays of handles.
        self.newline()
        write('template <typename T>', file=self.outFile)
        write('static void MapHandleArray(const format::HandleId*   ids,', file=self.outFile)
        write('                           T*                        handles,', file=self.outFile)
        write('                           size_t                    len,', file=self.outFile)
        write('                           const VulkanObjectMapper& object_mapper,', file=self.outFile)
        write('                           T (VulkanObjectMapper::*MapFunc)(format::HandleId) const)', file=self.outFile)
        write('{', file=self.outFile)
        write('    if ((ids != nullptr) && (handles != nullptr))', file=self.outFile)
        write('    {', file=self.outFile)
        write('        for (size_t i = 0; i < len; ++i)', file=self.outFile)
        write('        {', file=self.outFile)
        write('            handles[i] = (object_mapper.*MapFunc)(ids[i]);', file=self.outFile)
        write('        }', file=self.outFile)
        write('    }', file=self.outFile)
        write('}', file=self.outFile)

        # Implement a utility function to be used for adding arrays of handles.
        self.newline()
        write('template <typename T>', file=self.outFile)
        write('static void AddHandleArray(const format::HandleId*   ids,', file=self.outFile)
        write('                           size_t                    ids_len,', file=self.outFile)
        write('                           const T*                  handles,', file=self.outFile)
        write('                           size_t                    handles_len,', file=self.outFile)
        write('                           VulkanObjectMapper&       object_mapper,', file=self.outFile)
        write('                           void (VulkanObjectMapper::*AddFunc)(format::HandleId, T))', file=self.outFile)
        write('{', file=self.outFile)
        write('    if ((ids != nullptr) && (handles != nullptr))', file=self.outFile)
        write('    {', file=self.outFile)
        write('        // TODO: Improved handling of array size mismatch.', file=self.outFile)
        write('        size_t len = std::min(ids_len, handles_len);', file=self.outFile)
        write('        for (size_t i = 0; i < len; ++i)', file=self.outFile)
        write('        {', file=self.outFile)
        write('            (object_mapper.*AddFunc)(ids[i], handles[i]);', file=self.outFile)
        write('        }', file=self.outFile)
        write('    }', file=self.outFile)
        write('}', file=self.outFile)

    # Method override
    def endFile(self):
        # Generate the pNext handle mapping code.
        self.newline()
        write('void MapPNextStructHandles(const void* value, void* wrapper, const VulkanObjectMapper& object_mapper)', file=self.outFile)
        write('{', file=self.outFile)
        write('    if ((value != nullptr) && (wrapper != nullptr))', file=self.outFile)
        write('    {', file=self.outFile)
        write('        const VkBaseInStructure* base = reinterpret_cast<const VkBaseInStructure*>(value);', file=self.outFile)
        write('', file=self.outFile)
        write('        switch (base->sType)', file=self.outFile)
        write('        {', file=self.outFile)
        write('        default:', file=self.outFile)
        write('            // TODO: Report or raise fatal error for unrecongized sType?', file=self.outFile)
        write('            break;', file=self.outFile)
        for baseType in self.pNextStructs:
            write('        case {}:'.format(self.pNextStructs[baseType]), file=self.outFile)
            write('            MapStructHandles(reinterpret_cast<Decoded_{}*>(wrapper), object_mapper);'.format(baseType), file=self.outFile)
            write('            break;', file=self.outFile)
        write('        }', file=self.outFile)
        write('    }', file=self.outFile)
        write('}', file=self.outFile)

        # Generate handle adding functions for output structs with handles
        for struct in self.outputStructsWithHandles:
            self.newline()
            write(self.makeStructHandleAdditions(struct, self.structsWithHandles[struct]), file=self.outFile)

        self.newline()
        write('GFXRECON_END_NAMESPACE(decode)', file=self.outFile)
        write('GFXRECON_END_NAMESPACE(gfxrecon)', file=self.outFile)

        # Finish processing in superclass
        BaseGenerator.endFile(self)

    #
    # Method override
    def genStruct(self, typeinfo, typename, alias):
        BaseGenerator.genStruct(self, typeinfo, typename, alias)

        if not alias:
            if self.checkStructMemberHandles(typename, self.structsWithHandles):
                # Track this struct if it can be present in a pNext chain, for generating the MapPNextStructHandles code.
                parentStructs = typeinfo.elem.get('structextends')
                if parentStructs:
                    sType = self.makeStructureTypeEnum(typeinfo, typename)
                    if sType:
                        self.pNextStructs[typename] = sType

    #
    # Method override
    def genCmd(self, cmdinfo, name, alias):
        BaseGenerator.genCmd(self, cmdinfo, name, alias)

        # Look for output structs that contain handles and add to list
        if not alias:
            for valueInfo in self.featureCmdParams[name][2]:
                if self.isOutputParameter(valueInfo) and \
                (valueInfo.baseType in self.getFilteredStructNames()) and \
                (valueInfo.baseType in self.structsWithHandles) and \
                (valueInfo.baseType not in self.outputStructsWithHandles):
                    self.outputStructsWithHandles.append(valueInfo.baseType)

    #
    # Indicates that the current feature has C++ code to generate.
    def needFeatureGeneration(self):
        if self.featureStructMembers:
            return True
        return False

    #
    # Performs C++ code generation for the feature.
    def generateFeature(self):
        for struct in self.getFilteredStructNames():
            if struct in self.structsWithHandles:
                members = self.structsWithHandles[struct]

                # Determine if the struct only contains members that are structs that contain handles, and does not contain handles directly.
                structsOnly = True
                for member in members:
                    if self.isHandle(member.baseType):
                        structsOnly = False
                        break

                body = '\n'
                body += 'void MapStructHandles(Decoded_{}* wrapper, const VulkanObjectMapper& object_mapper)\n'.format(struct)
                body += '{\n'

                if structsOnly:
                    body += '    if (wrapper != nullptr)\n'
                    body += '    {'
                else:
                    body += '    if ((wrapper != nullptr) && (wrapper->decoded_value != nullptr))\n'
                    body += '    {\n'
                    body += '        {}* value = wrapper->decoded_value;\n'.format(struct)

                body += self.makeStructHandleMappings(struct, members)
                body += '    }\n'
                body += '}'

                write(body, file=self.outFile)

    #
    # Generating expressions for mapping struct handles read from the capture file to handles created at replay.
    def makeStructHandleMappings(self, name, members):
        body = ''

        for member in members:
            body += '\n'

            if 'pNext' in member.name:
                body += '        if (wrapper->pNext)\n'
                body += '        {\n'
                body += '            MapPNextStructHandles(wrapper->pNext->GetPointer(), wrapper->pNext->GetMetaStructPointer(), object_mapper);\n'
                body += '        }\n'
            elif self.isStruct(member.baseType):
                # This is a struct that includes handles.
                if member.isArray:
                    body += '        MapStructArrayHandles<Decoded_{}>(wrapper->{name}->GetMetaStructPointer(), wrapper->{name}->GetLength(), object_mapper);\n'.format(member.baseType, name=member.name)
                elif member.isPointer:
                    body += '        MapStructArrayHandles<Decoded_{}>(wrapper->{}->GetMetaStructPointer(), 1, object_mapper);\n'.format(member.baseType, member.name)
                else:
                    body += '        MapStructHandles(wrapper->{}.get(), object_mapper);\n'.format(member.name)
            else:
                # If it is an array or pointer, map with the utility function.
                if (member.isArray or member.isPointer):
                    if member.isArray:
                        body += '        MapHandleArray<{type}>(wrapper->{name}.GetPointer(), wrapper->{name}.GetHandlePointer(), wrapper->{name}.GetLength(), object_mapper, &VulkanObjectMapper::Map{type});\n'.format(type=member.baseType, name=member.name)
                    else:
                        body += '        MapHandleArray<{type}>(wrapper->{name}.GetPointer(), wrapper->{name}.GetHandlePointer(), 1, object_mapper, &VulkanObjectMapper::Map{type});\n'.format(type=member.baseType, name=member.name)
                else:
                    body += '        value->{name} = object_mapper.Map{}(wrapper->{name});\n'.format(member.baseType, name=member.name)

        return body

    #
    # Generating expressions for adding mappings for handles created at replay that are embedded in structs
    def makeStructHandleAdditions(self, name, members):
        body = 'void AddStructHandles(const Decoded_{name}* id_wrapper, const {name}* handle_struct, VulkanObjectMapper& object_mapper)\n'.format(name=name)
        body +='{\n'
        body +='    if (id_wrapper != nullptr)\n'
        body +='    {\n'

        for member in members:

            if 'pNext' in member.name:
                body += '        if (id_wrapper->pNext)\n'
                body += '        {\n'
                body += '            AddPNextStructHandles(id_wrapper->pNext->GetPointer(), id_wrapper->pNext->GetMetaStructPointer(), handle_struct->pNext, object_mapper);\n'
                body += '        }\n'
            elif self.isStruct(member.baseType):
                # This is a struct that includes handles.
                if member.isArray:
                    body += '        AddStructArrayHandles<Decoded_{}>(id_wrapper->{name}->GetMetaStructPointer(), id_wrapper->{name}->GetLength(), handle_struct->{name}, static_cast<size_t>(handle_struct->{length}), object_mapper);\n'.format(member.baseType, name=member.name, length=member.arrayLength)
                elif member.isPointer:
                    body += '        AddStructArrayHandles<Decoded_{}>(id_wrapper->{name}->GetMetaStructPointer(), 1, handle_struct->{name}, 1, object_mapper);\n'.format(member.baseType, name=member.name)
                else:
                    body += '        AddStructHandles(id_wrapper->{name}.get(), &handle_struct->{name}, object_mapper);\n'.format(name=member.name)
            else:
                # If it is an array or pointer, add with the utility function.
                if (member.isArray or member.isPointer):
                    if member.isArray:
                        body += '        AddHandleArray<{type}>(id_wrapper->{name}.GetPointer(), id_wrapper->{name}.GetLength(), handle_struct->{name}, handle_struct->{length}, object_mapper, &VulkanObjectMapper::Add{type});\n'.format(type=member.baseType, name=member.name, length=member.arrayLength)
                    else:
                        body += '        AddHandleArray<{type}>(id_wrapper->{name}.GetPointer(), 1, handle_struct->{name}, 1, object_mapper, &VulkanObjectMapper::Add{type});\n'.format(type=member.baseType, name=member.name)
                else:
                    body += '        object_mapper.Add{type}(id_wrapper->{name}, handle_struct->{name});\n'.format(type=member.baseType, name=member.name)

        body += '    }\n'
        body += '}'
        return body
