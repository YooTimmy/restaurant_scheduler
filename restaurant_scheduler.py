import collections
from ortools.sat.python import cp_model
import plotly.figure_factory as ff
import pandas as pd

plan_date = pd.to_datetime('08/01/2021 09:00:00')

def visualize_schedule(assigned_jobs,all_staffs,plan_date):
    final = []
    for staff in all_staffs:
        assigned_jobs[staff].sort()
        for assigned_task in assigned_jobs[staff]:
            name = 'Order_%i' % assigned_task.job
            temp = dict(Task=staff,Start=plan_date + pd.DateOffset(minutes = assigned_task.start),
                        Finish= plan_date + pd.DateOffset(minutes = (assigned_task.start + assigned_task.duration)),
                        Resource=name)
            final.append(temp)
    final.sort(key = lambda x: x['Task'])
    return final


def Restaurant_Planner():
    """To demonstrate how to use Google OR-Tools as a planner for restaurant"""
    # Create the model.
    model = cp_model.CpModel()

    jobs_data = [ #order = (staff, processing_time). step 1: Ingredient Preparation, Step 2: Cooking, Step 3: Serving
        [(0, 3), (1, 6), (2, 2)],  # Order 0
        [(0, 2), (2, 3), (1, 3)],  # Order 1
        [(0, 2), (1, 7), (2, 1)]  # Order 2
    ]

    staff_count = 1 + max(task[0] for job in jobs_data for task in job)
    all_staffs = range(staff_count)

    # Computes horizon dynamically as the sum of all durations.
    horizon = sum(task[1] for job in jobs_data for task in job)

    # Named tuple to store information about created variables.
    task_type = collections.namedtuple('task_type', 'start end interval')
    # Named tuple to manipulate solution information.
    assigned_task_type = collections.namedtuple('assigned_task_type',
                                                'start job index duration')

    # Creates job intervals and add to the corresponding staff lists.
    all_tasks = {}
    staff_to_intervals = collections.defaultdict(list)

    for job_id, job in enumerate(jobs_data):
        for task_id, task in enumerate(job):
            staff = task[0]
            duration = task[1]
            suffix = '_%i_%i' % (job_id, task_id)
            start_var = model.NewIntVar(0, horizon, 'start' + suffix)
            end_var = model.NewIntVar(0, horizon, 'end' + suffix)
            interval_var = model.NewIntervalVar(start_var, duration, end_var, 'interval' + suffix)
            all_tasks[job_id, task_id] = task_type(start=start_var,
                                                   end=end_var,
                                                   interval=interval_var)
            staff_to_intervals[staff].append(interval_var)

    # Create and add disjunctive constraints.
    for staff in all_staffs:
        model.AddNoOverlap(staff_to_intervals[staff])

    # Precedences inside a job.
    for job_id, job in enumerate(jobs_data):
        for task_id in range(len(job) - 1):
            model.Add(all_tasks[job_id, task_id + 1].start >= all_tasks[job_id, task_id].end)
            # Make sure the time gap of task 2 and task 3 are less then 3 mins
            if task_id == 1:
                model.Add(all_tasks[job_id, task_id + 1].start <= all_tasks[job_id, task_id].end + 3)
            else:
                continue

    # Final objective - minimize the total time spent to complete all orders
    obj_var = model.NewIntVar(0, horizon, 'total_time')
    model.AddMaxEquality(obj_var, [all_tasks[job_id, len(job) - 1].end for job_id, job in enumerate(jobs_data)])
    model.Minimize(obj_var)

    # Solve model.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        # Create one list of assigned tasks per machine.
        assigned_jobs = collections.defaultdict(list)
        for job_id, job in enumerate(jobs_data):
            for task_id, task in enumerate(job):
                staff = task[0]
                assigned_jobs[staff].append(
                    assigned_task_type(start=solver.Value(all_tasks[job_id, task_id].start),
                                       job=job_id,
                                       index=task_id,
                                       duration=task[1]))

        res = visualize_schedule(assigned_jobs,all_staffs,plan_date)
        fig = ff.create_gantt(res, index_col='Resource', show_colorbar=True, group_tasks=True)
        fig.show()
        # Finally, print the solution found.
        print('Optimal Schedule Length: %i' % solver.ObjectiveValue())


Restaurant_Planner()


