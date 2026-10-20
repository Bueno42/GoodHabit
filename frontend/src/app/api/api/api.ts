export * from './token.service';
import { TokenService } from './token.service';
export * from './v1.service';
import { V1Service } from './v1.service';
export const APIS = [TokenService, V1Service];
