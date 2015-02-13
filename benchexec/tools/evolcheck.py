"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging
import os
import platform
import tempfile
import subprocess
import hashlib
import xml.etree.ElementTree as ET

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    previousStatus = None

    def executable(self):
        return util.find_executable('evolcheck_wrapper')


    def version(self, executable):
        return subprocess.Popen([executable, '--version'],
                                stdout=subprocess.PIPE).communicate()[0].strip()

    def name(self):
        return 'eVolCheck'

    def preprocessSourcefile(self, sourcefile):
        gotoCcExecutable      = util.find_executable('goto-cc')
        # compile with goto-cc to same file, bith '.cc' appended
        self.preprocessedFile = sourcefile + ".cc"

        subprocess.Popen([gotoCcExecutable,
                            sourcefile,
                            '-o',
                            self.preprocessedFile],
                          stdout=subprocess.PIPE).wait()

        return self.preprocessedFile


    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        sourcefile = sourcefiles[0]
        sourcefile = self.preprocessSourcefile(sourcefile)

        # also append '.cc' to the predecessor-file
        if '--predecessor' in options :
            options[options.index('--predecessor') + 1] = options[options.index('--predecessor') + 1] + '.cc'

        return [executable] + [sourcefile] + options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if not os.path.isfile(self.preprocessedFile):
            return 'ERROR (goto-cc)'

        status = None

        assertionHoldsFound         = False
        verificationSuccessfulFound = False
        verificationFailedFound     = False

        for line in output:
            if 'A real bug found.' in line:
                status = result.STATUS_FALSE_REACH
            elif 'VERIFICATION SUCCESSFUL' in line:
                verificationSuccessfulFound = True
            elif 'VERIFICATION FAILED' in line:
                verificationFailedFound = True
            elif 'ASSERTION(S) HOLD(S)' in line:
                assertionHoldsFound = True
            elif 'The program models are identical' in line:
                status = self.previousStatus
            elif 'Assertion(s) hold trivially.' in line:
                status = result.STATUS_TRUE_PROP

        if status is None:
            if verificationSuccessfulFound and not verificationFailedFound:
                status = result.STATUS_TRUE_PROP
            else:
                status = result.STATUS_UNKNOWN

        self.previousStatus = status

        return status
