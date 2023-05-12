import multiprocessing as mp
import numpy as np
from typing import Optional, List
import copy
from scipy.optimize import minimize
import matplotlib.pyplot as plt

from simojio.lib.ModuleInputContainer import ModuleInputContainer
from simojio.lib.VariationContainer import VariationContainer
from simojio.lib.OptimizationResultsContainer import OptimizationResultsContainer
from simojio.lib.ModuleLoader import ModuleLoader
from simojio.lib.module_executor.CurrentVariablesAndResultsContainer import CurrentVariablesAndResultsContainer
from simojio.lib.module_executor.shared_functions import plot_optimization_steps
from simojio.lib.abstract_modules import Calculator, Fitter

plt.rcParams.update({'figure.max_open_warning': 0})  # mute warning "More than 20 figures have been opened"


class SingleModuleProcess:

    def __init__(self):

        self.module = None
        self.optimization_queue = None
        self.result_queue = None
        self.global_queue = None
        self.stop_queue = None

        self.variable_values_store = list()
        self.optimization_values = list()

    def run(self, module_name: str, input_container: ModuleInputContainer,
            result_queue: mp.Queue, save_path: str, optimization_queue: mp.Queue,
            global_queue: mp.Queue, stop_queue: mp.Queue):

        self.initialize_module(module_name, result_queue, save_path)
        self._set_queues(result_queue, optimization_queue, global_queue, stop_queue)
        self.configure_and_run_module(input_container)

    def run_coupled(self, module_name: str, input_queue: mp.Queue, result_queue: mp.Queue, save_path: str,
                    optimization_queue: mp.Queue, global_queue: mp.Queue, stop_queue: mp.Queue):

        self.initialize_module(module_name, result_queue, save_path)
        self._set_queues(result_queue, optimization_queue, global_queue, stop_queue)

        while True:
            self._check_for_termination()
            try:
                next_task = input_queue.get_nowait()
                if next_task is None:
                    # Poison pill means shutdown
                    input_queue.task_done()
                    break
                else:
                    self.configure_and_run_module(*next_task)  # next_task = [InputContainer, variable_values_list]
                    input_queue.task_done()
            except:
                pass

    def run_optimization(self, module_name: str, result_queue: mp.Queue,
                         save_path: str, optimization_queue: mp.Queue, global_queue: mp.Queue, stop_queue: mp.Queue,
                         variation_container: VariationContainer, evaluation_set_idx: int, opt_value_name: str,
                         method: str, maximize: bool, max_iter: int):

        self.variable_values_store = []
        self.optimization_values = []

        self.initialize_module(module_name, result_queue, save_path)
        self._set_queues(result_queue, optimization_queue, global_queue, stop_queue)

        # optimize with sending changed parameters only
        initial_variable_values = variation_container.get_varied_variables_values(evaluation_set_idx)
        variable_bounds = variation_container.get_varied_variables_bounds(evaluation_set_idx)

        # run once with current parameter values to initialize all values which are not set to variables
        input_container = variation_container.get_input_container_single(evaluation_set_idx)
        self.configure_and_run_module(input_container)

        if isinstance(self.module, Fitter):
            maximize = False
            opt_value_name, opt_value = self.module.get_fit_name_and_value()

        result = minimize(self._optimization_fct,
                          x0=np.array(initial_variable_values),
                          method=method,
                          options={'maxiter': max_iter},
                          bounds=variable_bounds,
                          args=(variation_container, evaluation_set_idx, opt_value_name, maximize))

        # show results
        results_container = OptimizationResultsContainer()
        results_container.set_results(optimized_value_name=opt_value_name,
                                      variable_names=variation_container.get_varied_variables_names(evaluation_set_idx),
                                      variable_bounds=variable_bounds,
                                      solver_name=method,
                                      maximize=maximize,
                                      results_obj=result)

        self.result_queue.put(results_container)

    def configure_and_run_module(self, next_task: ModuleInputContainer, variable_values: Optional[List[float]] = None):

        self.module.generic_parameters = next_task.generic_parameters
        self.module.evaluation_set_parameters = next_task.evaluation_set_parameters

        if self.module.has_layers():
            self.module.layer_list = next_task.layer_list

        self.module.run()
        results_dict = {}
        if isinstance(self.module, Calculator) or isinstance(self.module, Fitter):
            results_dict = self.module.get_results_dict()

        current_variables_and_results = CurrentVariablesAndResultsContainer(results_dict, variable_values)
        self.result_queue.put(current_variables_and_results)

        return results_dict

    def initialize_module(self, module_name: str, result_queue: mp.Queue, save_path: str):

        module_loader = ModuleLoader()
        self.module = copy.deepcopy(module_loader.load_module(module_name))
        self.module.queue = result_queue
        self.module.simoji_save_dir = save_path
        self.module.__init__()

    def _optimization_fct(self, variable_values: List[float], variation_container: VariationContainer,
                          evaluation_set_idx: int, optimization_value_name: str, maximize: bool):

        self._check_for_termination()

        input_container = variation_container.get_input_container_optimization(evaluation_set_idx, variable_values)
        results_dict = self.configure_and_run_module(input_container, variable_values)

        optimization_value = results_dict[optimization_value_name]
        variable_names = variation_container.get_varied_variables_names(evaluation_set_idx)

        self.variable_values_store.append(variable_values)
        self.optimization_values.append(optimization_value)

        plot_optimization_steps(optimization_values=self.optimization_values,
                                optimization_value_name=optimization_value_name,
                                variable_values_list=self.variable_values_store,
                                variable_names=variable_names,
                                queue=self.result_queue)

        if maximize:
            return -optimization_value
        else:
            return optimization_value

    @staticmethod
    def _get_process_name() -> str:
        return mp.current_process().name

    def _set_queues(self, result_queue: mp.Queue, optimization_queue: mp.Queue, global_queue: mp.Queue,
                    stop_queue: mp.Queue):
        self.optimization_queue = optimization_queue
        self.result_queue = result_queue
        self.global_queue = global_queue
        self.stop_queue = stop_queue

    def _check_for_termination(self):
        stop_msg = None
        try:
            stop_msg = self.stop_queue.get_nowait()
        except:
            pass
        if stop_msg is not None:
            raise ValueError("Terminate optimization of " + self._get_process_name())


if __name__ == "__main__":
    pass
