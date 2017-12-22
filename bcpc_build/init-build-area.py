#!/usr/bin/env python3
from build_unit import BuildUnit
from build_unit import BuildUnitAllocator
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    allocator = BuildUnitAllocator()
    allocator.setup()
    build = allocator.allocate()
    allocator.provision(build)
    print(build.to_json())
