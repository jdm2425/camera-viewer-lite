/*General Libraries*/
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <Python.h>

/*Thorlabs Libraries*/
#include <visa.h>
#include <TLDFM.h>
#include <TLDFMX.h>
#include <TLDSTP.h>


/*Define Deformable Mirror Parameters*/
//Number of segments in each ring tier of the mirror
#define PDFMTOT 40
#define tiltanglemaximum 180.00
#define tiltangleminimum -180.00
#define tiltamplitudemaximum 0.1
#define tiltamplitudeminimum 0.0
#define SegAmpLimiter 100.0
#define Seg1RelRange 10.0
#define Seg2RelRange 10.0
#define Seg3RelRange 20.0
#define TEMPINPUTPOWER 0.000400


/*Define Computational Parameters*/
#define NumParents 60
#define ChildrenPerParent 6
#define MinPercentage 0.5
#define AcceptPercentage 0.50
#define MaxPercentage 0.8
#define RealGainMargin 0.005



/*Create a data type to keep each generation of children in.
    Index is the ranking of the power of that child,
    voltages is the array of voltages for each mirror segment,
    mutations is the array of mutations for each voltage,
    tiltangle is the angle at which the mirror is to be tilted
    tiltamplitude relative amplitude at which the mirror will be tilted,
    tiltanglemutation is the mutation for the mirror tilt angle,
    tiltamplitudemutation is the mutation for the mirror tilt amplitude,
    output is the power from that configuration */
typedef struct
{
    double voltages[PDFMTOT];
    double mutations[PDFMTOT];
    double tiltangle;
    double tiltamplitude;
    double tiltanglemutation;
    double tiltamplitudemutation;
    double output;
} childlist;


typedef struct
{

    int rank;
    double voltages[PDFMTOT];
    double mutations[PDFMTOT];
    double tiltangle;
    double tiltamplitude;
    double tiltanglemutation;
    double tiltamplitudemutation;
    double output;
} tempchildlist;



typedef struct
{
    int rank;
    double output;
} ranklist;




#ifdef _CVI_
   #define EXIT_SUCCESS 0
   #define EXIT_FAILURE 1
#endif

/*Test, sample data structure*/
typedef struct
{
  ViUInt8 firstHighByte;
  ViUInt8 firstLowByte;
  ViUInt8 secondHighByte;
  ViUInt8 secondLowByte;
} SAMPLE_dword_converter_t;

/*Test, sample types for output word*/
typedef union
{
  SAMPLE_dword_converter_t byteRepresentation;
  ViUInt32                 dwordRepresentation;
} SAMPLE_dword_t;




void error_exit(ViSession instrHdl, ViStatus err)
{
   ViChar buf[TLDFM_ERR_DESCR_BUFER_SIZE];

   // Get error description and print out error
   TLDFM_error_message(instrHdl, err, buf);
   fprintf(stderr, "\nERROR: %s\n", buf);

   // close session to instrument if open
   if(VI_NULL != instrHdl)
   {
      TLDFM_close(instrHdl);
   }

   // exit program
   printf("\nThe program is shutting down.\n");
   getchar();

   exit (EXIT_FAILURE);
}

ViStatus select_instrument(ViChar **resource)
{
	ViStatus err;
	ViUInt32 deviceCount = 0;
	int      choice = 0;

	ViChar    manufacturer[TLDFM_BUFFER_SIZE];
	ViChar    instrumentName[TLDFM_MAX_INSTR_NAME_LENGTH];
    ViChar    serialNumber[TLDFM_MAX_SN_LENGTH];
    ViBoolean deviceAvailable;
    ViChar    resourceName[VI_FIND_BUFLEN];

	printf("Scanning for instruments...\n");
	err = TLDFM_get_device_count(VI_NULL, &deviceCount);
	if((VI_ERROR_RSRC_NFOUND == err) || (0 == deviceCount))
	{
		printf("No matching instruments found\n\n");
		return err;
	}

	printf("Found %d matching instrument(s):\n\n", (int) deviceCount);

	for(ViUInt32 i = 0; i < deviceCount;)
	{
		err = TLDFM_get_device_information(VI_NULL,
										   i,
										   manufacturer,
										   instrumentName,
										   serialNumber,
										   &deviceAvailable,
										   resourceName);

		printf("%d:\t%s\t%s\tS/N:%s\t%s\n",
				(int) ++i,
				manufacturer,
				instrumentName,
				serialNumber,
				deviceAvailable ? "available" : "locked");
	}

	if(2 <= deviceCount)
	{
		ViBoolean deviceSelected = VI_FALSE;
		printf("\nPlease choose: ");
		do
		{
			do
			{
				choice = getchar();
			}
			while(EOF == choice);

			if((0 >= choice) || (deviceCount < choice))
			{
				printf("Invalid choice\n\n");
				choice = EOF;
			}
			else
			{
				deviceSelected = VI_TRUE;
			}
		}
		while(!deviceSelected);
	}
	else
	{
		choice = 1;
		printf("\nPress any key to continue");
		getchar();
	}

	err = TLDFM_get_device_information(VI_NULL,
									   (ViUInt32)(choice - 1),
									   manufacturer,
									   instrumentName,
									   serialNumber,
									   &deviceAvailable,
									   resourceName);

	if(VI_SUCCESS == err)
	{
		*resource = malloc(VI_FIND_BUFLEN);
		strncpy(*resource, resourceName, VI_FIND_BUFLEN);
	}
	return err;
}


//General function to generate pairs of random Gaussian numbers
void gaussiannumbers(int segment, double inputarray[] ){
int i = segment;
int ip1 = i + 1;
double n1, n2, f;
do {
    n1 = (2 * rand()/(double)RAND_MAX) - 1;
    n2 = (2 * rand()/(double)RAND_MAX) - 1;
    f = (n1 * n1) + (n2 * n2);
    } while (f>=1);

    f = sqrt((-2*log(f))/f );
    inputarray[i]=n1*f;
    inputarray[ip1]=n2*f;

}

void getvoltageranges (int segment,double returnrange[2], double *voltageranges[3][2]){

    if (segment<=7){
        returnrange[0]= (double) *voltageranges[0][0];
        returnrange[1]= (double) *voltageranges[0][1];

    }   

    else if (segment >=24){
        returnrange[0]= (double) *voltageranges[2][0];
        returnrange[1]= (double) *voltageranges[2][1];

    }

    else {
        returnrange[0]= (double) *voltageranges[1][0];
        returnrange[1]= (double) *voltageranges[1][1];

    }
}

void deformer(){

    printf("\nTLFDM Checkpoint 1\n");
    srand(time(NULL));
    int child, parent, parentloop, childloop, i, j, l;                                                     //Looping Variables
    int segment,escapelocalmaximum,escapestaticpower,certainty;                                                   //Identifier integers
    double power, oldbest=0.0,  entrypower, finishcriteria, voltage,result,voltagerange,voltagemean,realmaximumvoltage,realminimumvoltage,calcfraction,oldpowercheck,gainmargin;
    int parent1, parent2,chooseparent, choosemutation, NumChildren, FamilySize, tempparentcount, tempparenttracker, numentries;
    double multiplier1, multiplier2, multiplier3, multiplier4, newvoltage, newtiltangle, newtiltamplitude, maximumvoltage, minimumvoltage, tiltangle, tiltamplitude;
    double mutationlist[PDFMTOT], tiltanglemutationlist[PDFMTOT], tiltamplitudemutationlist[PDFMTOT];
    double *voltageranges[3][2],rangebox[3][2],limits[3]={Seg1RelRange,Seg2RelRange,Seg3RelRange},voltagelimits[2];
    double testvar1,testvar2,testvar3,testvar4,testvar5,testvar6;
    double check1, check2, check3, checkmean;
    
    printf("\nLet's see if we find a power meter anywhere.\n");
    PyObject* myModuleString = PyUnicode_FromString((char*)"ReadPowermeter");
    PyObject* myModule = PyImport_Import(myModuleString);
    PyObject* LoadPowermeter = PyObject_GetAttrString(myModule,(char*)"LoadPowerMeter");
    PyObject* ReadPower = PyObject_GetAttrString(myModule,(char*)"QuickReader");
    PyObject* powermeter=PyObject_CallObject(LoadPowermeter,NULL);
	
	
    certainty=0;
    NumChildren = NumParents * ChildrenPerParent;
    FamilySize  = NumChildren + NumParents;

    childlist parents[NumParents], children[NumChildren], bestchild;
    tempchildlist *tempparents;
    ranklist rankings[FamilySize];

    printf("\nBegin processing code! Press enter to continue if a power meter was found.");
    getchar();


    ViStatus  err;
    ViChar    *rscPtr;
    ViSession instrHdl = VI_NULL;
    ViUInt32  vi, Segments, TiltElements;
    ViReal64  VoltageMirrorMin, VoltageMirrorMax, VoltageMirrorCommon;
    ViReal64  VoltageTiltMin, VoltageTiltMax, VoltageTiltCommon;
    ViReal64  SegmentVoltages[PDFMTOT];
    ViReal64  TiltAmplitude, TiltAngle;
    //ViReal64  FeedbackVoltage, FeedbackCurrent, MonitorVoltage;
    //ViReal64  SegmentVoltage;

    err = select_instrument(&rscPtr);
    if(VI_SUCCESS != err){error_exit(instrHdl, err);}
    err = TLDFM_init(rscPtr, VI_TRUE, VI_TRUE, &instrHdl);
    if(err) error_exit(instrHdl, err);
    err = TLDFM_get_device_configuration(instrHdl,
                                        &Segments,
                                        &VoltageMirrorMin,
                                        &VoltageMirrorMax,
                                        &VoltageMirrorCommon,
                                        &TiltElements,
                                        &VoltageTiltMin,
                                        &VoltageTiltMax,
                                        &VoltageTiltCommon);

    if(err) {error_exit(instrHdl, err);}
    printf("\n");
    printf("Number of Segments        :  %2d\n", (int) Segments);
    printf("Min. Voltage              :  %8.3f\n", VoltageMirrorMin);
    printf("Max. Voltage              :  %8.3f\n", VoltageMirrorMax);
    printf("\n");
    printf("No. of Tip/Tilt Elements  :  %2d\n", (int) TiltElements);
    printf("Min. Voltage              :  %8.3f\n", VoltageTiltMin);
    printf("Max. Voltage              :  %8.3f\n", VoltageMirrorMax);
    
    //Sanity checks
    if(PDFMTOT != (int) Segments){
        printf("Segment count mismatch: PDFMTOT = %d, Segments = %d", PDFMTOT, (int) Segments );
        exit(0);
    }

    //Initialise the mirror position
    for (segment=0;segment<Segments;segment++){
        parents[0].voltages[segment]=100;
        tiltamplitude = 0;
        parents[0].tiltamplitude=tiltamplitude;
        tiltangle = 0;
        parents[0].tiltangle=tiltangle;
    }
    for(i = 0; i < Segments; i++){
        vi = (ViReal64) i;
        SegmentVoltages[vi] =  (ViReal64) parents[0].voltages[i];
    }
    TiltAngle =     (ViReal64) parents[0].tiltangle;
    TiltAmplitude = (ViReal64) parents[0].tiltamplitude;
    err = TLDFM_set_segment_voltages(instrHdl, SegmentVoltages);
    TLDFM_set_tilt_amplitude_angle (instrHdl, TiltAmplitude, TiltAngle);
    if(err) error_exit(instrHdl, err);
    
    realmaximumvoltage = (double) VoltageMirrorMax;
    realminimumvoltage = (double) VoltageMirrorMin;
    voltagerange = (realmaximumvoltage - realminimumvoltage);
    voltagemean  =  voltagerange/2;
    calcfraction=voltagerange*((double) 1-1/SegAmpLimiter); //limits[3],Seg2RelRange,Seg2RelRange, Seg3RelRange

    for (i=0; i<3; i++){
        minimumvoltage =voltagemean - (voltagerange*limits[i]/(2*SegAmpLimiter));
        maximumvoltage =voltagemean + (voltagerange*limits[i]/(2*SegAmpLimiter));
        rangebox[i][0] = minimumvoltage;
        rangebox[i][1] = maximumvoltage;
    }
    
    for (i=0; i<3; i++){
        for (j=0; j<2; j++){ 
            voltageranges[i][j] = &rangebox[i][j];
        }
    }


    getvoltageranges(7,voltagelimits,*voltageranges);
    testvar1=voltagelimits[0];
    testvar2=voltagelimits[1];
    getvoltageranges(15,voltagelimits,*voltageranges);
    testvar3=voltagelimits[0];
    testvar4=voltagelimits[1];
    getvoltageranges(31,voltagelimits,*voltageranges);     
    testvar5=voltagelimits[0];
    testvar6=voltagelimits[1];
    printf("\nVoltage ranges are:\nSegments 0-7:%lf to %lf V\nSegments 8-23:%lf to %lf V\nSegments 24-39:%lf to %lf V",testvar1,testvar2,testvar3,testvar4,testvar5,testvar6);
    
    printf("\nTLFDM Checkpoint 2\n");
    printf("\nPlease check that the parameters above match what you expect from the deformable mirror.\nThen press enter to continue.\n");
    getchar();
    



    printf("Could you please just pop the power meter in front of the fibre, so we can get an initial power reader?\nThanks\nJust press enter when you've done it.\n");
    getchar();

    /*Begin initialization of the first generation of parents*/
    PyObject* myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
    result = PyFloat_AsDouble(myResult);
    entrypower=TEMPINPUTPOWER;
    finishcriteria=entrypower*AcceptPercentage;
    
    printf("Great, so our input power is %lf, which means we'll automatically end the program if we get above %lf.\n",entrypower,finishcriteria);

    printf("\nI'm now going to pause until the power meter is after the fibre.\nSo go on, put it after the fibre.\nRun along now.\nDon't keep me waiting...");
    getchar();


    /*Generate original parents and mutations*/
    //Generate parent voltages, tilt angle and tilt amplitude
    for (parent=0;parent<NumParents;parent++){
        for (segment=0;segment<Segments;segment++){
            getvoltageranges(segment,voltagelimits,*voltageranges);
            minimumvoltage=voltagelimits[0];
            maximumvoltage=voltagelimits[1];
            voltage=(((double) rand()/RAND_MAX)*(maximumvoltage-minimumvoltage))+minimumvoltage;
            parents[parent].voltages[segment]=voltage;
            tiltamplitude = ((double) rand()/RAND_MAX)*tiltamplitudemaximum;
            parents[parent].tiltamplitude=tiltamplitude;
            tiltangle = (2*(((double) rand()/RAND_MAX)-0.5))*tiltanglemaximum;
            parents[parent].tiltangle=tiltangle;
        }
    }

    //Generate voltage and tilt mutations
    for (parent=0;parent<NumParents;parent++){
        for (segment=0;segment<Segments;segment+=2){
            gaussiannumbers(segment,mutationlist);
            gaussiannumbers(segment,tiltanglemutationlist);
            gaussiannumbers(segment,tiltamplitudemutationlist);
        }
        for (segment=0;segment<Segments;segment++){
            getvoltageranges(segment,voltagelimits,*voltageranges);
            minimumvoltage=voltagelimits[0];
            maximumvoltage=voltagelimits[1];
            parents[parent].mutations[segment] = mutationlist[segment] * ((maximumvoltage - minimumvoltage)/100);
            parents[parent].tiltanglemutation  = tiltanglemutationlist[segment] * ((tiltanglemaximum - tiltangleminimum)/100);
            parents[parent].tiltamplitudemutation = tiltamplitudemutationlist[segment] * ((tiltamplitudemaximum - tiltamplitudeminimum)/100);
        }
    }

    /*Read power for original parents*/
    for (parentloop=0;parentloop<NumParents;parentloop++){
        for(i = 0; i < Segments; i++){
            vi = (ViReal64) i;
            SegmentVoltages[vi] =  (ViReal64) parents[parentloop].voltages[i];
        }

        err = TLDFM_set_segment_voltages(instrHdl, SegmentVoltages);
        if(err) error_exit(instrHdl, err);
        myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
        result = PyFloat_AsDouble(myResult);
        power=result;
        printf("%lf\n",power);
        parents[parentloop].output=power;
    }

    /*End initialization*/
    printf("Let's do this thing.\nPress enter to continue");
    getchar();
    printf("\nI know what must be done...\n");
    /*Start geneteic mutations*/
    FILE *testfile=fopen("ParentData.txt","w+");

    while(certainty==0){

        fprintf(testfile,"\nNew Generation\n");
        for (parent = 0; parent<NumParents; parent++){
            fprintf(testfile,"%.9lf output with ",parents[parent].output);
            for (l=0;l<PDFMTOT;l++){
                fprintf(testfile,"(%lf, %lf),",parents[parent].voltages[l],parents[parent].mutations[l]);
            }
        fprintf(testfile,"\n");
        }

        /*Create the new generation of children*/
        for (childloop=0;childloop<NumChildren;childloop++){
            multiplier1=((double) rand()/RAND_MAX)*(NumParents-1);
            parent1=multiplier1;
            multiplier2=((double) rand()/RAND_MAX)*(NumParents-1);
            parent2=multiplier2;


            //Voltage inheritance
            for (segment=0;segment<Segments;segment++){
                getvoltageranges(segment,voltagelimits,*voltageranges);
                minimumvoltage=voltagelimits[0];
                maximumvoltage=voltagelimits[1];
                multiplier3=((double) rand()/RAND_MAX);
                chooseparent=2*multiplier3;
                if      (chooseparent==0) {children[childloop].voltages[segment]=parents[parent1].voltages[segment];}
                else if (chooseparent==1 || chooseparent==2) {children[childloop].voltages[segment]=parents[parent2].voltages[segment];}
                else                      {printf("\nERROR. Could not pick a valid parent voltage. Choosing %d",chooseparent);getchar();}
                multiplier4=((double) rand()/RAND_MAX);
                choosemutation=2*multiplier4;
                if      (choosemutation==0) {children[childloop].mutations[segment]=parents[parent1].mutations[segment];}
                else if (choosemutation==1 || choosemutation==2) {children[childloop].mutations[segment]=parents[parent2].mutations[segment];}
                else                      {printf("\nERROR. Could not pick a valid parent voltage mutation. Choosing %d",chooseparent);getchar();}

                newvoltage=children[childloop].voltages[segment] + children[childloop].mutations[segment];
                if ((newvoltage>= maximumvoltage) || (newvoltage <= minimumvoltage)){
                    newvoltage = children[childloop].voltages[segment] - children[childloop].mutations[segment];
                    if ((newvoltage>= maximumvoltage) || (newvoltage <= minimumvoltage)){
                        printf("\nERROR. The combination of segment voltage and mutation was not valid.");
                        printf("\nInhereted voltage is %lf, mutation is %lf", children[childloop].voltages[segment],children[childloop].mutations[segment]);
                        newvoltage=(((double) rand()/RAND_MAX)*(maximumvoltage-minimumvoltage))+minimumvoltage;
                        getchar();
                        }
                }
                children[childloop].voltages[segment]=newvoltage;
            }

            //Tilt angle inheritance
            multiplier3=((double) rand()/RAND_MAX);
            chooseparent=2*multiplier3;
            if      (chooseparent==0) {children[childloop].tiltangle=parents[parent1].tiltangle;}
            else if (chooseparent==1 || chooseparent==2) {children[childloop].tiltangle=parents[parent2].tiltangle;}
            else                      {printf("\nERROR. Could not pick a valid parent tilt angle. Choosing %d",chooseparent);getchar();}
            multiplier4=((double) rand()/RAND_MAX);
            choosemutation=2*multiplier4;
            if      (choosemutation==0) {children[childloop].tiltanglemutation=parents[parent1].tiltanglemutation;}
            else if (choosemutation==1 || choosemutation==2) {children[childloop].tiltanglemutation=parents[parent2].tiltanglemutation;}
            else                      {printf("\nERROR. Could not pick a valid parent tilt angle mutation. Choosing %d",chooseparent);getchar();}

            newtiltangle=children[childloop].tiltangle + children[childloop].tiltanglemutation;
            if ((newtiltangle>= tiltanglemaximum) || (newtiltangle <= tiltangleminimum)){
                newtiltangle = children[childloop].tiltangle - children[childloop].tiltanglemutation;
                if ((newtiltangle>= tiltanglemaximum) || (newtiltangle <= tiltangleminimum)){
                    printf("\nERROR. The combination of tilt angle and tilt angle mutation was not valid.");
                    printf("\nInhereted tilt angle is %lf, mutation is %lf", children[childloop].tiltangle,children[childloop].tiltanglemutation);
                    getchar();
                }
            }
            children[childloop].tiltangle=newtiltangle;

            //Tilt amplitude inheritance
            multiplier3=((double) rand()/RAND_MAX);
            chooseparent=2*multiplier3;
            if      (chooseparent==0) {children[childloop].tiltamplitude=parents[parent1].tiltamplitude;}
            else if (chooseparent==1 || chooseparent==2) {children[childloop].tiltamplitude=parents[parent2].tiltamplitude;}
            else                      {printf("\nERROR. Could not pick a valid parent tilt amplitude. Choosing %d",chooseparent);getchar();}
            multiplier4=((double) rand()/RAND_MAX);
            choosemutation=2*multiplier4;
            if      (choosemutation==0) {children[childloop].tiltamplitudemutation=parents[parent1].tiltamplitudemutation;}
            else if (choosemutation==1 || choosemutation==2) {children[childloop].tiltamplitudemutation=parents[parent2].tiltamplitudemutation;}
            else                      {printf("\nERROR. Could not pick a valid parent tilt amplitude mutation. Choosing %d",chooseparent);getchar();}

            newtiltamplitude=children[childloop].tiltamplitude + children[childloop].tiltamplitudemutation;
            if ((newtiltamplitude>= tiltamplitudemaximum) || (newtiltamplitude <= tiltamplitudeminimum)){
                newtiltamplitude = children[childloop].tiltamplitude - children[childloop].tiltamplitudemutation;
                if ((newtiltamplitude>= tiltamplitudemaximum) || (newtiltamplitude <= tiltamplitudeminimum)){
                    printf("\nERROR. The combination of tilt amplitude and tilt amplitude mutation was not valid.");
                    printf("\nInhereted tilt amplitude is %lf, mutation is %lf", children[childloop].tiltamplitude,children[childloop].tiltamplitudemutation);
                    getchar();
                    }
            }
            children[childloop].tiltamplitude=newtiltamplitude;

        }
        printf("\nFinished making the new children for this generation.");

        for (childloop=0;childloop<NumChildren;childloop++){
            for(i = 0; i < Segments; i++){
                vi = (ViReal64) i;
                SegmentVoltages[vi] =  (ViReal64) children[childloop].voltages[i];
            }
            TiltAngle =     (ViReal64) children[childloop].tiltangle;
            TiltAmplitude = (ViReal64) children[childloop].tiltamplitude;
            err = TLDFM_set_segment_voltages(instrHdl, SegmentVoltages);
            if(err) error_exit(instrHdl, err);
            err = TLDFM_set_tilt_amplitude_angle (instrHdl, TiltAmplitude, TiltAngle);
            if(err) error_exit(instrHdl, err);
            myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
            result = PyFloat_AsDouble(myResult);
            power=result;
            children[childloop].output=power;
        }


        for (parentloop=0;parentloop<NumParents;parentloop++){
            for(i = 0; i < Segments; i++){
                vi = (ViReal64) i;
                SegmentVoltages[vi] =  (ViReal64) parents[parentloop].voltages[i];
            }
            TiltAngle =     (ViReal64) parents[parentloop].tiltangle;
            TiltAmplitude = (ViReal64) parents[parentloop].tiltamplitude;
            err = TLDFM_set_segment_voltages(instrHdl, SegmentVoltages);
            if(err) error_exit(instrHdl, err);
            err = TLDFM_set_tilt_amplitude_angle (instrHdl, TiltAmplitude, TiltAngle);
            if(err) error_exit(instrHdl, err);
            myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
            result = PyFloat_AsDouble(myResult);
            power=result;
            parents[parentloop].output=power;
            if (parentloop==0){sleep(5);}
        }

        printf("\nTaken power readings for all the parents and children in this generation.");



        /*Start ranking all the parents and children */
        //Initialize ranking variables
        numentries=1;
        rankings[0].output=children[0].output;
        rankings[0].rank=0;
        
        //Rank Children
        for (child=1; child<NumChildren; child++){
            rankings[child].output=children[child].output;
            rankings[child].rank = 0;
            for (i=0;i<numentries; i++){

                if(rankings[child].output>rankings[i].output){
                    rankings[i].rank += 1;
                }
                else{
                    rankings[child].rank += 1;
                }
            }
            numentries++;
        }
        
        
        //Rank Parents
        for (parent=0; parent<NumParents; parent++){
            parentloop=parent+NumChildren;
            rankings[parentloop].output=parents[parent].output;
            rankings[parentloop].rank = 0;
            for (i=0;i<numentries; i++){

                if(rankings[parentloop].output>rankings[i].output){
                    rankings[i].rank += 1;
                }
                else{
                    rankings[parentloop].rank += 1;
                }
            }
            numentries++;
        }

        printf("\nFinished ranking the parents and children.");

        /*Begin storing the strong parents from the previous generations in a temporary array to prevent them from being overwritten*/
        //Identify number of temporary parents needed for creating the next generation
        tempparentcount = 0;
        tempparenttracker = 0;
        for (parent=0;parent<NumParents;parent++){
            parentloop=parent + NumChildren;
            if (rankings[parentloop].rank<NumParents) {tempparentcount+=1;}
        }

        //Allocate memory and create the array for the temporary parents
        tempparents = (tempchildlist*) malloc(tempparentcount*sizeof(tempchildlist));

        //Copy the strong parents data into the temporary parents array
        for (parent=0;parent<NumParents;parent++){
            parentloop=parent + NumChildren;
            if (rankings[parentloop].rank<tempparentcount) {
                tempparents[tempparenttracker].rank                  = rankings[parentloop].rank;
                tempparents[tempparenttracker].output                = parents[parent].output;
                tempparents[tempparenttracker].tiltangle             = parents[parent].tiltangle ;
                tempparents[tempparenttracker].tiltamplitude         = parents[parent].tiltamplitude ;
                tempparents[tempparenttracker].tiltanglemutation     = parents[parent].tiltanglemutation ;
                tempparents[tempparenttracker].tiltamplitudemutation = parents[parent].tiltamplitudemutation ;
                for (l=0;l<PDFMTOT;l++){
                    tempparents[tempparenttracker].voltages[l]  = parents[parent].voltages[l];
                    tempparents[tempparenttracker].mutations[l] = parents[parent].mutations[l];
                }
            tempparenttracker++;
            }
        }

        /*Copy best parents and children into the parent array*/
        //Copy best parents from the temporary parent array into the parents array
        for (parent=0;parent<NumParents;parent++){
            for (parentloop=0; parentloop<tempparenttracker; parentloop++){
                if (tempparents[parentloop].rank==parent){
                    printf("\nNew parent %d is old parent %d, which is rank %d",parent,parentloop,tempparents[parentloop].rank);
                    parents[parent].output                = tempparents[parentloop].output;
                    parents[parent].tiltangle             = tempparents[parentloop].tiltangle;
                    parents[parent].tiltamplitude         = tempparents[parentloop].tiltamplitude;
                    parents[parent].tiltanglemutation     = tempparents[parentloop].tiltanglemutation;
                    parents[parent].tiltamplitudemutation = tempparents[parentloop].tiltamplitudemutation;
                    for (l=0;l<PDFMTOT;l++){
                        parents[parent].voltages[l]  = tempparents[parentloop].voltages[l];
                        parents[parent].mutations[l] = tempparents[parentloop].mutations[l];
                    }
                }
            }
        }
        escapelocalmaximum=0;
        //Copy the best children from the children array into the parents array
        for (parent=0;parent<NumParents;parent++){
            for (child=0; child<NumChildren; child++){
                if (rankings[child].rank==parent){
                    escapelocalmaximum=1;
                    printf("\nNew parent %d is child %d, which is rank %d",parent,child,rankings[child].rank);
                    parents[parent].output                = children[child].output;
                    parents[parent].tiltangle             = children[child].tiltangle ;
                    parents[parent].tiltamplitude         = children[child].tiltamplitude ;
                    parents[parent].tiltanglemutation     = children[child].tiltanglemutation ;
                    parents[parent].tiltamplitudemutation = children[child].tiltamplitudemutation ;
                    for (l=0;l<PDFMTOT;l++){
                        parents[parent].voltages[l]  = children[child].voltages[l];
                        parents[parent].mutations[l] = children[child].mutations[l];
                    }
                }
            }
        }

        //Free the temporary parents array
        free(tempparents);

        oldbest=parents[0].output;        
        gainmargin= (oldbest - oldpowercheck)/oldbest;
        if (gainmargin<=RealGainMargin){
            escapelocalmaximum=0;
        }

        if (escapelocalmaximum==0){
            printf("\nLooks like we're stuck in a local maximum");
            for (parent=30;parent<NumParents;parent++){
                for (segment=0;segment<Segments;segment++){
                    getvoltageranges(segment,voltagelimits,*voltageranges);
                    minimumvoltage=voltagelimits[0];
                    maximumvoltage=voltagelimits[1];
                    voltage=(((double) rand()/RAND_MAX)*(maximumvoltage-minimumvoltage))+minimumvoltage;
                    parents[parent].voltages[segment]=voltage;
                    tiltamplitude = ((double) rand()/RAND_MAX)*tiltamplitudemaximum;
                    parents[parent].tiltamplitude=tiltamplitude;
                    tiltangle = (2*(((double) rand()/RAND_MAX)-0.5))*tiltanglemaximum;
                    parents[parent].tiltangle=tiltangle;
                }
            }
        
            //Generate voltage and tilt mutations
            for (parent=30;parent<NumParents;parent++){
                for (segment=0;segment<Segments;segment+=2){
                    gaussiannumbers(segment,mutationlist);
                    gaussiannumbers(segment,tiltanglemutationlist);
                    gaussiannumbers(segment,tiltamplitudemutationlist);
                }
                for (segment=0;segment<Segments;segment++){
                    getvoltageranges(segment,voltagelimits,*voltageranges);
                    minimumvoltage=voltagelimits[0];
                    maximumvoltage=voltagelimits[1];
                    parents[parent].mutations[segment] = mutationlist[segment] * ((maximumvoltage - minimumvoltage)/100);
                    parents[parent].tiltamplitudemutation = tiltamplitudemutationlist[segment] * ((tiltamplitudemaximum - tiltamplitudeminimum)/100);
                    parents[parent].tiltanglemutation  = tiltanglemutationlist[segment] * ((tiltanglemaximum - tiltangleminimum)/100);
                }
            }
            
        }



        oldpowercheck=oldbest;
        printf("\nBest this round was %lf",oldbest);
        if (oldbest>=finishcriteria){
            for(vi = 0; vi < Segments; vi++){
                i = (int) vi;
                SegmentVoltages[vi] =  (ViReal64) parents[0].voltages[i];
            }
        TiltAngle           =   (ViReal64) parents[0].tiltangle;
        TiltAmplitude       =   (ViReal64) parents[0].tiltamplitude;
        err = TLDFM_set_segment_voltages(instrHdl, SegmentVoltages);
        err = TLDFM_set_tilt_amplitude_angle (instrHdl, TiltAmplitude, TiltAngle);;
        if(err) error_exit(instrHdl, err);
            myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
            result = PyFloat_AsDouble(myResult);
            check1=result;
            myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
            result = PyFloat_AsDouble(myResult);
            check2=result;
            myResult = PyObject_CallFunctionObjArgs(ReadPower,(powermeter),NULL);
            result = PyFloat_AsDouble(myResult);
            check3=result;
            checkmean = (check1 + check2 + check3) /3;
            if (checkmean>=finishcriteria){
                printf("\nWe have certainty! Power is %lf\n",checkmean);
                certainty=1;
            }
            else {
                printf("\nClose, but certainty not achieved, actual mean was %lf",checkmean);
                getchar();
            }
        }
        
    }

    TiltAngle =     (ViReal64) parents[0].tiltangle;
    TiltAmplitude = (ViReal64) parents[0].tiltamplitude;
    err = TLDFM_set_tilt_amplitude_angle (instrHdl, TiltAmplitude, TiltAngle);
    if(err) error_exit(instrHdl, err);



    FILE *finalconfig=fopen("BestConfig.txt","w+");
    //Set the voltages to that of the strongest child
    bestchild.output=parents[0].output;
    for (l=0;l<PDFMTOT;l++){
        bestchild.voltages[l]   =   parents[0].voltages[l];
        fprintf(finalconfig,"%lf, ",parents[0].voltages[l]);
    }
    bestchild.tiltangle     =   parents[0].tiltangle;
    bestchild.tiltamplitude =   parents[0].tiltamplitude;
    
    for(vi = 0; vi < Segments; vi++){
        i = (int) vi;
        SegmentVoltages[vi] =   (ViReal64) bestchild.voltages[i];
    }

    TiltAngle           =   (ViReal64) bestchild.tiltangle;
    TiltAmplitude       =   (ViReal64) bestchild.tiltamplitude;
    err = TLDFM_set_segment_voltages(instrHdl, SegmentVoltages);
    err = TLDFM_set_tilt_amplitude_angle (instrHdl, TiltAmplitude, TiltAngle);
    if(err) error_exit(instrHdl, err);
    sleep(600);

}
