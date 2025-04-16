import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as dotenv from 'dotenv';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
// import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';

dotenv.config();

export class LewasBackendInfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // The code that defines your stack goes here

    // example resource
    // const queue = new sqs.Queue(this, 'LewasBackendInfraQueue', {
    //   visibilityTimeout: cdk.Duration.seconds(300)
    // });

    // Check environment variables first
    const API_KEY = process.env.API_KEY;
    if (!API_KEY) {
      throw new Error("API_KEY environment variable is not set");
    }

    const DYNAMODB_TABLE_NAME = process.env.DYNAMODB_TABLE_NAME;
    if (!DYNAMODB_TABLE_NAME) {
      throw new Error("DYNAMODB_TABLE_NAME environment variable is not set");
    }
    const DYNAMODB_TABLE_NAME_ANIMAL = process.env.DYNAMODB_TABLE_NAME_ANIMAL;
    if (!DYNAMODB_TABLE_NAME_ANIMAL) {
      throw new Error("DYNAMODB_TABLE_NAME_ANIMAL environment variable is not set");
    }


    // Create the Lambda function
    const apiFunction = new lambda.DockerImageFunction(this, 'ApiFunction', {
      code: lambda.DockerImageCode.fromImageAsset('../image', {
        cmd: ["main.handler"]
      }),
      memorySize: 512,
      timeout: cdk.Duration.seconds(60),
      architecture: lambda.Architecture.ARM_64,
      environment: {
        API_KEY,
        DYNAMODB_TABLE_NAME,
        DYNAMODB_TABLE_NAME_ANIMAL
      },
    });

    const table_lewas = dynamodb.Table.fromTableName(this, 'UsersTable', DYNAMODB_TABLE_NAME);
    table_lewas.grantReadWriteData(apiFunction);

    const table_animal_test = dynamodb.Table.fromTableName(this, 'AnimalsTable', DYNAMODB_TABLE_NAME_ANIMAL);
    table_animal_test.grantReadWriteData(apiFunction);

    // Add function URL
    const functionUrl = apiFunction.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
    });

    apiFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [`${table_animal_test.tableArn}/index/*`],
      effect: iam.Effect.ALLOW,
    }));

    apiFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [`${table_lewas.tableArn}/index/*`],
      effect: iam.Effect.ALLOW,
    }));

    // Outputs
    new cdk.CfnOutput(this, 'FunctionUrl', {
      value: functionUrl.url,
      description: 'URL for the Lambda function',
    });
  }
}