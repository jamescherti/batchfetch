;;; Directory Local Variables for a Python project -*- no-byte-compile: t; -*-
;; Requires:
;;   - python-lsp-server: https://github.com/python-lsp/python-lsp-server
;;   - ruff: https://github.com/astral-sh/ruff
;;   - python-lsp-ruff: https://github.com/python-lsp/python-lsp-ruff
;;   - pylint: https://github.com/pylint-dev/pylint
;;   - pylsp-mypy: https://github.com/python-lsp/pylsp-mypy

((nil . ((sentence-end-double-space . nil)
         (require-final-newline . t)))
 (python-base-mode
  . ((indent-tabs-mode . nil)
     (tab-width . 4)
     (python-indent-offset . 4)
     (fill-column . 88)
     (eglot-workspace-configuration
      . (:pylsp
         (:plugins
          (:ruff
           (;; Ruff plugin (Requires: ruff and python-lsp-ruff)
            :enabled t
            :formatEnabled t
            ;; I: Sort imports
            ;; :extendSelect ["I"]
            ;; :format ["I"]
            )

           :pylsp_mypy
           (;; Type checking (Requires: pylsp-mypy)
            :enabled t
            ;; Disabling live mode prevents type-checking updates on every edit.
            ;; Save the file to refresh mypy diagnostics.
            :live_mode :json-false)

           :pylint (:enabled t)
           :flake8 (:enabled :json-false)
           :mccabe (:enabled :json-false)
           :pyflakes (:enabled :json-false)
           :pycodestyle (:enabled :json-false)
           :pydocstyle (:enabled :json-false)
           :isort (:enabled :json-false)

           :autopep8 (:enabled :json-false)
           :yapf (:enabled :json-false)

           :jedi_completion
           (;; Jedi code completion
            :enabled t
            :include_class_objects t
            :include_function_objects t
            :include_params t))))))))
