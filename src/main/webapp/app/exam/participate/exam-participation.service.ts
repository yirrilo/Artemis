import { Injectable } from '@angular/core';
import { SERVER_API_URL } from 'app/app.constants';
import { Observable } from 'rxjs';
import { StudentExam } from 'app/entities/student-exam.model';
import { HttpClient } from '@angular/common/http';
import { LocalStorageService } from 'ngx-webstorage';
import { Submission } from 'app/entities/submission.model';
import { ModelingSubmissionService } from 'app/exercises/modeling/participate/modeling-submission.service';
import { ProgrammingSubmissionService } from 'app/exercises/programming/participate/programming-submission.service';
import { TextSubmissionService } from 'app/exercises/text/participate/text-submission.service';
import { FileUploadSubmissionService } from 'app/exercises/file-upload/participate/file-upload-submission.service';
import { Exercise, ExerciseType } from 'app/entities/exercise.model';
import { ModelingSubmission } from 'app/entities/modeling-submission.model';
import { tap } from 'rxjs/operators';
import { TextSubmission } from 'app/entities/text-submission.model';

@Injectable({ providedIn: 'root' })
export class ExamParticipationService {
    set examId(value: number) {
        this._examId = value;
    }
    set courseId(value: number) {
        this._courseId = value;
    }
    private studentExam: StudentExam;
    private submissionSyncList: Submission[] = [];

    private _courseId: number;
    private _examId: number;

    // autoTimerInterval in seconds
    autoSaveTime = 60;
    autoSaveInterval: number;

    constructor(
        private httpClient: HttpClient,
        private localStorageService: LocalStorageService,
        private modelingSubmissionService: ModelingSubmissionService,
        private programmingSubmissionService: ProgrammingSubmissionService,
        private textSubmissionService: TextSubmissionService,
        private fileUploadSubmissionService: FileUploadSubmissionService,
    ) {}

    private getLocalStorageKeyForStudentExam(): string {
        const prefix = 'artemis_student_exam';
        return `${prefix}_${this._courseId}_${this._examId}`;
    }

    private getResourceUrl(): string {
        return `${SERVER_API_URL}api/courses/${this._courseId}/exams/${this._examId}`;
    }

    public getStudentExam(): Observable<StudentExam> {
        // TODO: check local storage
        const localStoredExam: StudentExam = this.localStorageService.retrieve(this.getLocalStorageKeyForStudentExam());

        if (localStoredExam) {
            this.studentExam = localStoredExam;
            return Observable.of(this.studentExam);
        } else {
            // download student exam from server on service init
            return this.getStudentExamFromServer().pipe(
                tap((studentExam: StudentExam) => {
                    this.studentExam = studentExam;
                }),
            );
        }
    }

    /**
     * Retrieves a {@link StudentExam} from server
     */
    private getStudentExamFromServer(): Observable<StudentExam> {
        // TODO: change this as soon as the server route changes
        const url = this.getResourceUrl() + '/studentExams/19/conduction';
        // this._courseId, this._examId
        return this.httpClient.get<StudentExam>(url);
    }

    /**
     * start AutoSaveTimer
     */
    public startAutoSaveTimer(): void {
        // auto save of submission if there are changes
        this.autoSaveInterval = window.setInterval(() => {
            this.synchronizeSubmissionsWithServer();
        }, 1000 * this.autoSaveTime);
    }

    /**
     * creates submissions for all submissions in SubmissionSaveList
     */
    private synchronizeSubmissionsWithServer() {
        // TODO: handle synchronization properly
        // TODO: map all submissions to observables and join them, at the end clear sync list
        this.submissionSyncList.forEach((submission) => {
            switch (submission.participation.exercise?.type) {
                case ExerciseType.TEXT:
                    this.textSubmissionService.create(submission as TextSubmission, submission.participation.exercise?.id);
                    break;
                case ExerciseType.FILE_UPLOAD:
                    return this.fileUploadSubmissionService;
                case ExerciseType.MODELING:
                    this.modelingSubmissionService.create(submission as ModelingSubmission, submission.participation.exercise.id).subscribe(
                        (response) => {
                            submission = response.body!;
                            submission.participation.submissions = [submission];
                            this.onSaveSuccess();
                        },
                        () => this.onSaveError(),
                    );
                    break;
                case ExerciseType.PROGRAMMING:
                    return this.programmingSubmissionService;
                case ExerciseType.QUIZ:
                    // TODO find submissionService
                    return null;
            }
        });
        // clear sync list
        this.submissionSyncList = [];
    }

    private onSaveSuccess() {
        console.log('saved');
    }

    private onSaveError() {
        console.log('error while saving');
    }

    /**
     * Updates StudentExam on server
     * @param studentExam
     */
    createSubmission(submission: Submission, exerciseId: number) {
        // update immediately in localStorage and online every 60seconds
        this.localStorageService.store(this.getLocalStorageKeyForStudentExam(), JSON.stringify(this.studentExam));
        // TODO: Add to updates
        this.submissionSyncList.push(submission);
    }

    getLatestSubmissionForParticipation(participationId: number): Observable<Submission | undefined> {
        const latestSubmission: Submission | undefined = this.submissionSyncList.find((submission) => submission.participation.id === participationId);
        if (!latestSubmission) {
            const exercise: Exercise | undefined = this.studentExam.participations.find((participation) => participation.id === participationId)?.exercise;
            switch (exercise?.type) {
                case ExerciseType.TEXT:
                    return this.textSubmissionService.getTextSubmissionForExerciseWithoutAssessment(exercise?.id);
                case ExerciseType.FILE_UPLOAD:
                    return this.fileUploadSubmissionService.getFileUploadSubmissionForExerciseWithoutAssessment(exercise?.id);
                case ExerciseType.MODELING:
                    return this.modelingSubmissionService.getLatestSubmissionForModelingEditor(participationId);
                case ExerciseType.PROGRAMMING:
                    return this.programmingSubmissionService.getProgrammingSubmissionForExerciseWithoutAssessment(exercise?.id);
                // case ExerciseType.QUIZ:
                // TODO find submissionService
                // return null;
            }
        }
        return Observable.of(latestSubmission);
    }
}
