import { Body, Controller, Put } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { UpdateChainConfigDto } from './admin.dto';
import { AdminService } from './admin.service';

@ApiTags('admin')
@Controller('admin/config')
export class AdminController {
  constructor(private readonly adminService: AdminService) {}

  @Put()
  update(@Body() dto: UpdateChainConfigDto) {
    return this.adminService.updateChainConfig(dto);
  }
}

