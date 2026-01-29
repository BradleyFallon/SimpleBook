Testing
=======

Run the full suite:

.. code-block:: console

   alltests

Normalization tests:

.. code-block:: console

   normtest

Golden-file tests:

.. code-block:: console

   regtest <book-key>
   regtest <book-key> --regen

Notes
-----

- Golden JSON files live in ``tests/schema/json``.
- EPUB inputs live in ``tests/epubs``.
