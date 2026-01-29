Runbook
=======

Quick start
-----------

.. code-block:: console

   source ./activate
   regtest --list

Aliases
-------

The helper aliases are defined in:

.. literalinclude:: ../devtools/aliases.sh
   :language: bash

CLI Help
--------

Generated from the CLI help text:

.. literalinclude:: generated/cli_help.txt
   :language: text

Common workflows
----------------

- `regtest <book-key>`: compare preview output to the golden file.
- `regtest <book-key> --regen`: regenerate a golden file.
- `debug-epub <book-key>`: dump spine-item classification.
- `unpack-epub <book-key>`: unzip an EPUB for inspection.
- `unpack-all-epubs`: unzip every EPUB in tests.
- `normtest`: run normalization tests.
- `alltests`: run the full test suite.
